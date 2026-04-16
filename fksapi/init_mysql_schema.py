from db_mysql import init_database_and_tables


if __name__ == '__main__':
    info = init_database_and_tables()
    print(f"MySQL schema ready: {info['user']}@{info['host']}:{info['port']}/{info['database']}")
