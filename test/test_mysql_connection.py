import mysql.connector
from mysql.connector import Error
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mysql_connection():
    # 首先验证环境变量是否存在
    required_env_vars = ['MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_DATABASE']
    for var in required_env_vars:
        if not os.getenv(var):
            print(f"错误: 环境变量 {var} 未设置")
            return

    try:
        # 打印连接配置信息（不包含敏感信息）
        print(f"尝试连接到数据库：")
        print(f"主机: {os.getenv('MYSQL_HOST')}")
        print(f"端口: {os.getenv('MYSQL_PORT')}")
        print(f"数据库: {os.getenv('MYSQL_DATABASE')}")
        print(f"用户: {os.getenv('MYSQL_USER')}")
        print(f"Python版本: {sys.version}")
        print(f"MySQL Connector版本: {mysql.connector.__version__}")

        config = {
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT')),
            'database': os.getenv('MYSQL_DATABASE'),
            'use_pure': True,  # 使用纯Python实现，避免C扩展可能导致的段错误
            'raise_on_warnings': os.getenv('MYSQL_RAISE_ON_WARNINGS', 'True') == 'True',
            'auth_plugin': os.getenv('MYSQL_AUTH_PLUGIN', 'mysql_native_password'),
            'connection_timeout': int(os.getenv('MYSQL_CONNECTION_TIMEOUT', '10')),
            'get_warnings': True,
            'buffered': True  # 使用缓冲查询，避免内存问题
        }

        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            db_info = connection.get_server_info()
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"成功连接到MySQL数据库！")
            print(f"服务器版本: {db_info}")
            print(f"当前数据库: {db_name}")
            cursor.close()
    except Error as e:
        print(f"连接MySQL时出错：")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        if isinstance(e, mysql.connector.errors.InterfaceError):
            print("提示：请检查数据库服务是否正在运行，以及主机名和端口是否正确")
        elif isinstance(e, mysql.connector.errors.ProgrammingError):
            print("提示：请检查用户名、密码和数据库名是否正确")
    except Exception as e:
        print(f"发生未预期的错误：")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("MySQL连接已关闭。")

if __name__ == '__main__':
    test_mysql_connection()