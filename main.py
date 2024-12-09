import re
import os
import argparse

def parse_java_entity(file_path):
    """
    Parse the Java entity class and extract table and column information.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    table_name = None
    columns = []

    for i, line in enumerate(lines):
        # Match @Table(name = "...")
        table_match = re.search(r'@Table\(name\s*=\s*"(.*?)"\)', line)
        if table_match:
            table_name = table_match.group(1)

        # Match @Column(name = "...")
        column_match = re.search(r'@Column\(name\s*=\s*"(.*?)"\)', line)
        if column_match:
            column_name = column_match.group(1)
            column_type = None

            # Check if annotation is on a field
            if i + 1 < len(lines):
                field_match = re.search(r'(private|protected|public)\s+(\w+)\s+\w+;', lines[i + 1])
                if field_match:
                    column_type = field_match.group(2)

            # Check if annotation is on a getter method
            if column_type is None:
                method_match = re.search(r'public\s+(\w+)\s+\w+\(\)', lines[i + 1])
                if method_match:
                    column_type = method_match.group(1)

            if column_type:
                columns.append((column_name, column_type))

    return table_name, columns

def map_java_type_to_db_type(java_type):
    """
    Map Java types to SQL types.
    """
    type_mapping = {
        'String': 'VARCHAR(255)',
        'int': 'INTEGER',
        'Integer': 'INTEGER',
        'long': 'BIGINT',
        'Long': 'BIGINT',
        'boolean': 'BOOLEAN',
        'Boolean': 'BOOLEAN',
        'Date': 'TIMESTAMP',
        'BigDecimal': 'DECIMAL(19,2)'
    }
    return type_mapping.get(java_type, 'VARCHAR(255)')

def generate_add_column_query(table_name, column_name, column_type):
    db_type = map_java_type_to_db_type(column_type)
    return f'<addColumn tableName="{table_name}">\n    <column name="{column_name}" type="{db_type}"/>\n</addColumn>', f'<dropColumn tableName="{table_name}" columnName="{column_name}"/>'

def generate_delete_column_query(table_name, column_name):
    return f'<dropColumn tableName="{table_name}" columnName="{column_name}"/>', f'<addColumn tableName="{table_name}">\n    <column name="{column_name}" type="VARCHAR(255)"/>\n</addColumn>'

def generate_modify_column_query(table_name, column_name, column_type):
    db_type = map_java_type_to_db_type(column_type)
    return f'<modifyDataType tableName="{table_name}" columnName="{column_name}" newDataType="{db_type}"/>', f'<modifyDataType tableName="{table_name}" columnName="{column_name}" newDataType="VARCHAR(255)"/>'

def generate_create_table_query(table_name, columns):
    xml_lines = [
        f'<createTable tableName="{table_name}">'
    ]
    rollback_lines = [
        f'<dropTable tableName="{table_name}"/>'
    ]
    for column_name, java_type in columns:
        db_type = map_java_type_to_db_type(java_type)
        xml_lines.append(f'    <column name="{column_name}" type="{db_type}"/>')
    xml_lines.append('</createTable>')
    return '\n'.join(xml_lines), '\n'.join(rollback_lines)

def main():
    parser = argparse.ArgumentParser(description="Generate Liquibase XML scripts.")
    parser.add_argument("-f", "--file", required=True, help="Path to the Java entity file")
    parser.add_argument("-c", "--add-column", nargs=2, metavar=("COLUMN_NAME", "COLUMN_TYPE"), help="Add a column")
    parser.add_argument("-d", "--delete-column", metavar="COLUMN_NAME", help="Delete a column")
    parser.add_argument("-m", "--modify-column", nargs=2, metavar=("COLUMN_NAME", "COLUMN_TYPE"), help="Modify a column type")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return

    try:
        table_name, columns = parse_java_entity(args.file)

        if args.add_column:
            column_name, column_type = args.add_column
            query, rollback_query = generate_add_column_query(table_name, column_name, column_type)
        elif args.delete_column:
            column_name = args.delete_column
            query, rollback_query = generate_delete_column_query(table_name, column_name)
        elif args.modify_column:
            column_name, column_type = args.modify_column
            query, rollback_query = generate_modify_column_query(table_name, column_name, column_type)
        else:
            if not table_name or not columns:
                print("Error: Could not parse table name or columns.")
                return
            query, rollback_query = generate_create_table_query(table_name, columns)

        output_file = args.file.replace('.java', '_liquibase_query.xml')
        with open(output_file, 'w') as file:
            file.write(f'<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write(f'<databaseChangeLog xmlns="http://www.liquibase.org/xml/ns/dbchangelog"\n')
            file.write(f'                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
            file.write(f'                  xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog\n')
            file.write(f'                  http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-3.8.xsd">\n')
            file.write(f'\n    <changeSet id="1" author="generated">\n')
            file.write(f'        {query}\n')
            file.write(f'        <rollback>\n            {rollback_query}\n        </rollback>\n')
            file.write(f'    </changeSet>\n')
            file.write(f'</databaseChangeLog>\n')

        print(f"Liquibase XML created successfully: {output_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
