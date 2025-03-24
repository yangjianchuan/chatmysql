import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mysql_connection():
    config = {
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT')),
        'database': os.getenv('MYSQL_DATABASE'),
        'raise_on_warnings': os.getenv('MYSQL_RAISE_ON_WARNINGS') == 'True',
        'auth_plugin': os.getenv('MYSQL_AUTH_PLUGIN'),
        'connection_timeout': int(os.getenv('MYSQL_CONNECTION_TIMEOUT'))
    }

    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            print("Successfully connected to the database.")
    except Error as e:
        print(f"Error while connecting to MySQL: {str(e)}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("MySQL connection is closed.")

if __name__ == '__main__':
    test_mysql_connection() 