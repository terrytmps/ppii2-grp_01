from .databaseHandler import get_db


# Builder for query help to simplify the syntax
# How to use it:
#
class QueryBuilder:

    # Set up the query
    def __init__(self, sql):
        self.sql = sql
        self.__db = get_db()
        self.__cursor = self.__db.cursor()

    # Execute the query and return the result
    def fetch_all(self) -> list:
        self.__cursor.execute(self.sql)
        return self.__cursor.fetchall()

    # Execute an update or delete something who alter the data
    def commit(self) -> None:
        self.__cursor.execute(self.sql)
        self.__db.commit()
