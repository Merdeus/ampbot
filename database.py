import sqlite3
import aiosqlite
import json
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = 'bot_database.db'):
        self.db_path = db_path
        self.max_history_entries = 1000
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin'))
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS instance_permissions (
                    user_id INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    start_permission INTEGER DEFAULT 0 CHECK(start_permission IN (0, 1)),
                    stop_permission INTEGER DEFAULT 0 CHECK(stop_permission IN (0, 1)),
                    status_permission INTEGER DEFAULT 0 CHECK(status_permission IN (0, 1)),
                    additional_permissions TEXT DEFAULT '{}',
                    PRIMARY KEY (user_id, instance_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    log TEXT NOT NULL,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id)
            ''')
            
            await db.commit()
    
    async def add_user(self, user_id: int, role: str = 'user'):
        if role not in ('user', 'admin'):
            raise ValueError("Role must be 'user' or 'admin'")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, role)
                VALUES (?, ?)
            ''', (user_id, role))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, role FROM users WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'user_id': row[0],
                        'role': row[1]
                    }
                return None
    
    async def update_user_role(self, user_id: int, role: str):
        if role not in ('user', 'admin'):
            raise ValueError("Role must be 'user' or 'admin'")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET role = ? WHERE user_id = ?
            ''', (role, user_id))
            await db.commit()
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, role FROM users
            ''') as cursor:
                rows = await cursor.fetchall()
                return [{'user_id': row[0], 'role': row[1]} for row in rows]
    
    async def set_instance_permission(self, user_id: int, instance_id: str,
                                     start_permission: bool = False,
                                     stop_permission: bool = False,
                                     status_permission: bool = False,
                                     additional_permissions: Optional[Dict[str, Any]] = None):
        additional_perms_json = json.dumps(additional_permissions or {})
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO instance_permissions 
                (user_id, instance_id, start_permission, stop_permission, status_permission, additional_permissions)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, instance_id, int(start_permission), int(stop_permission), 
                  int(status_permission), additional_perms_json))
            await db.commit()
    
    async def get_instance_permission(self, user_id: int, instance_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, instance_id, start_permission, stop_permission, 
                       status_permission, additional_permissions
                FROM instance_permissions 
                WHERE user_id = ? AND instance_id = ?
            ''', (user_id, instance_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'user_id': row[0],
                        'instance_id': row[1],
                        'start_permission': bool(row[2]),
                        'stop_permission': bool(row[3]),
                        'status_permission': bool(row[4]),
                        'additional_permissions': json.loads(row[5] or '{}')
                    }
                return None
    
    async def get_user_instance_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, instance_id, start_permission, stop_permission, 
                       status_permission, additional_permissions
                FROM instance_permissions 
                WHERE user_id = ?
            ''', (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [{
                    'user_id': row[0],
                    'instance_id': row[1],
                    'start_permission': bool(row[2]),
                    'stop_permission': bool(row[3]),
                    'status_permission': bool(row[4]),
                    'additional_permissions': json.loads(row[5] or '{}')
                } for row in rows]
    
    async def get_instance_permissions(self, instance_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, instance_id, start_permission, stop_permission, 
                       status_permission, additional_permissions
                FROM instance_permissions 
                WHERE instance_id = ?
            ''', (instance_id,)) as cursor:
                rows = await cursor.fetchall()
                return [{
                    'user_id': row[0],
                    'instance_id': row[1],
                    'start_permission': bool(row[2]),
                    'stop_permission': bool(row[3]),
                    'status_permission': bool(row[4]),
                    'additional_permissions': json.loads(row[5] or '{}')
                } for row in rows]
    
    async def delete_instance_permission(self, user_id: int, instance_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM instance_permissions 
                WHERE user_id = ? AND instance_id = ?
            ''', (user_id, instance_id))
            await db.commit()
    
    async def update_additional_permission(self, user_id: int, instance_id: str, 
                                          permission_key: str, permission_value: Any):
        perm = await self.get_instance_permission(user_id, instance_id)
        if not perm:
            raise ValueError(f"No permission found for user {user_id} and instance {instance_id}")
        
        additional_perms = perm['additional_permissions']
        additional_perms[permission_key] = permission_value
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE instance_permissions 
                SET additional_permissions = ?
                WHERE user_id = ? AND instance_id = ?
            ''', (json.dumps(additional_perms), user_id, instance_id))
            await db.commit()
    
    async def add_history(self, log: str, user_id: Optional[int] = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO history (log, user_id) VALUES (?, ?)
            ''', (log, user_id))
            
            async with db.execute('SELECT COUNT(*) FROM history') as cursor:
                count = (await cursor.fetchone())[0]
            
            if count > self.max_history_entries:
                await db.execute('''
                    DELETE FROM history 
                    WHERE id IN (
                        SELECT id FROM history 
                        ORDER BY timestamp ASC 
                        LIMIT ?
                    )
                ''', (count - self.max_history_entries,))
            
            await db.commit()
    
    async def get_history(self, limit: int = 100, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            if user_id is not None:
                async with db.execute('''
                    SELECT id, timestamp, log, user_id 
                    FROM history 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    return [{
                        'id': row[0],
                        'timestamp': row[1],
                        'log': row[2],
                        'user_id': row[3]
                    } for row in rows]
            else:
                async with db.execute('''
                    SELECT id, timestamp, log, user_id 
                    FROM history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [{
                        'id': row[0],
                        'timestamp': row[1],
                        'log': row[2],
                        'user_id': row[3]
                    } for row in rows]
    
    async def clear_history(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM history')
            await db.commit()
