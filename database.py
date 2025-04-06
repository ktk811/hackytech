import os
import sqlite3
import streamlit as st
from datetime import datetime
import json
import threading

# Thread-local storage for database connections
thread_local = threading.local()

# Remove global variables since we're using thread_local storage
_conn = None  # This is just to avoid errors in places where _conn might still be referenced

def get_db_path():
    """Get SQLite database path."""
    return "finance_tracker.db"

def initialize_db():
    """Initialize the SQLite database connection and create required tables if they don't exist."""
    try:
        # Connect to SQLite database with check_same_thread=False for Streamlit's threaded environment
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        # Configure row_factory to access rows as dictionaries
        conn.row_factory = sqlite3.Row
        
        # Create tables if they don't exist
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            zen_mode INTEGER DEFAULT 0,
            wants_budget REAL DEFAULT 100.0
        )
        ''')
        
        # Funds table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS funds (
            username TEXT PRIMARY KEY,
            balance REAL DEFAULT 0,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        ''')
        
        # Expenses table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            type TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        ''')
        
        # Goals table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            date_created TEXT,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        ''')
        
        # FinPet table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS finpet (
            username TEXT PRIMARY KEY,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            next_level_xp INTEGER DEFAULT 75,
            name TEXT DEFAULT 'Penny',
            last_fed TEXT,
            rewards TEXT DEFAULT '[]',
            FOREIGN KEY (username) REFERENCES users(username)
        )
        ''')
        
        # Check if 'rewards' column exists in finpet table, and add it if it doesn't
        try:
            cursor.execute("SELECT rewards FROM finpet LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE finpet ADD COLUMN rewards TEXT DEFAULT '[]'")
            
        conn.commit()
        
        # Store connection in thread_local
        thread_local.conn = conn
        
        # Set current time in session state for consistency across the app
        if "current_time" not in st.session_state:
            st.session_state.current_time = datetime.now()
        
        return True
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return False

def get_db():
    """Get the SQLite database instance with a document-like interface for compatibility."""
    # Check if we have a connection in thread_local storage
    if not hasattr(thread_local, 'conn'):
        # If not, initialize the database
        initialize_db()
    
    # Create a class that provides a document-style interface using SQLite
    class Collection:
        def __init__(self, conn, table_name):
            self.conn = conn
            self.table_name = table_name
            self._conn = conn  # For compatibility with other modules
            self._sort_field = None
            self._sort_direction = None
            self._projection = None
        
        def find_one(self, query):
            cursor = self.conn.cursor()
            
            # Handle id query
            if 'id' in query:
                cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (query['id'],))
                result = cursor.fetchone()
                if result:
                    # Convert sqlite3.Row to dictionary
                    return dict(result)
                return None
            
            # Handle username query (most common case)
            if 'username' in query:
                cursor.execute(f"SELECT * FROM {self.table_name} WHERE username = ?", (query['username'],))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
            
            return None
        
        def insert_one(self, document):
            cursor = self.conn.cursor()
            # Extract keys and values
            keys = list(document.keys())
            values = list(document.values())
            placeholders = ', '.join(['?' for _ in keys])
            columns = ', '.join(keys)
            
            # Insert the document
            cursor.execute(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})", values)
            self.conn.commit()
            # Get last inserted id
            last_id = cursor.lastrowid
            return {"id": last_id}
        
        def update_one(self, query, update):
            cursor = self.conn.cursor()
            # Handle the $set operator (most common case)
            if '$set' in update:
                set_values = update['$set']
                set_clause = ', '.join([f"{key} = ?" for key in set_values.keys()])
                values = list(set_values.values())
                
                # Handle username query (most common case)
                if 'username' in query:
                    values.append(query['username'])
                    cursor.execute(f"UPDATE {self.table_name} SET {set_clause} WHERE username = ?", values)
                    self.conn.commit()
                    return True
                
                # Handle id query
                if 'id' in query:
                    values.append(query['id'])
                    cursor.execute(f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?", values)
                    self.conn.commit()
                    return True
            return False
        
        def find(self, query=None, projection=None):
            cursor = self.conn.cursor()
            self._projection = projection
            # Build the SQL query
            fields = "*"
            if projection:
                projection_fields = [field for field, include in projection.items() if include]
                if projection_fields:
                    fields = ", ".join(projection_fields)
            sql_query = f"SELECT {fields} FROM {self.table_name}"
            params = []
            # Build WHERE clause
            where_clauses = []
            if query:
                # Handle basic username query
                if 'username' in query:
                    where_clauses.append("username = ?")
                    params.append(query['username'])
                # Handle $gte and $lte operators for date ranges or numeric fields
                for key, value in query.items():
                    if isinstance(value, dict):
                        for op, op_value in value.items():
                            if op == '$gte':
                                where_clauses.append(f"{key} >= ?")
                                params.append(op_value)
                            elif op == '$lte':
                                where_clauses.append(f"{key} <= ?")
                                params.append(op_value)
                # Handle direct value matches for other fields
                for key, value in query.items():
                    if key != 'username' and not isinstance(value, dict):
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
            if where_clauses:
                sql_query += " WHERE " + " AND ".join(where_clauses)
            # Add ORDER BY clause if sort is specified
            if self._sort_field:
                direction = "DESC" if self._sort_direction == -1 else "ASC"
                sql_query += f" ORDER BY {self._sort_field} {direction}"
            # Execute the query
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            result_list = [dict(zip(column_names, row)) for row in results]
            # Reset sort and projection settings
            self._sort_field = None
            self._sort_direction = None
            self._projection = None
            return result_list
        
        def sort(self, *args, **kwargs):
            """
            Set sorting parameters for the query.
            Supports both positional and keyword arguments:
            - sort("field", 1) or sort("field", -1)
            - sort(field="field", direction=1) or sort(field="field", direction=-1)
            """
            if args and len(args) >= 2:
                self._sort_field = args[0]
                self._sort_direction = args[1]
            elif kwargs:
                self._sort_field = kwargs.get('field')
                self._sort_direction = kwargs.get('direction')
            return self
    
    # Create a proxy object that provides a simple document-like interface over SQLite
    class DBProxy:
        def __init__(self, conn):
            self.conn = conn
            self._collections = {}
        
        def __getattr__(self, name):
            if name not in self._collections:
                self._collections[name] = Collection(self.conn, name)
            return self._collections[name]
    
    return DBProxy(thread_local.conn)
