# database.py - PhoneBook Database
import sqlite3
import csv
import os

class PhoneBookDB:
    def __init__(self, db_name="phonebook.db"):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_name = os.path.join(project_dir, db_name)
        self._init_db()
    
    def _get_conn(self):
        # Connect to DB
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        # Create contacts table
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                group_name TEXT NOT NULL,
                position TEXT,
                email TEXT,
                phone TEXT NOT NULL,
                photo_path TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print(f"DB ready: {self.db_name}")
    
    def add_contact(self, data):
        # Add new contact
        required = ['first_name', 'last_name', 'group_name', 'phone']
        for field in required:
            if not data.get(field):
                return False, f"Missing: {field}"
        
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO contacts 
                (first_name, last_name, group_name, position, email, phone, photo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('first_name', ''),
                data.get('last_name', ''),
                data.get('group_name', ''),
                data.get('position', ''),
                data.get('email', ''),
                data.get('phone', ''),
                data.get('photo_path', '')
            ))
            conn.commit()
            return True, f"Added (ID: {c.lastrowid})"
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()
    
    def get_all(self, sort_by='last_name'):
        # Get all contacts
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(f"SELECT * FROM contacts ORDER BY {sort_by}")
        result = [dict(row) for row in c.fetchall()]
        conn.close()
        return result
    
    def search(self, filters):
        # Search contacts
        conn = self._get_conn()
        c = conn.cursor()
        
        query = "SELECT * FROM contacts WHERE 1=1"
        params = []
        
        fields = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'group_name': 'group_name',
            'position': 'position',
            'email': 'email',
            'phone': 'phone'
        }
        
        for key, col in fields.items():
            if key in filters and filters[key]:
                query += f" AND {col} LIKE ?"
                params.append(f"%{filters[key]}%")
        
        query += " ORDER BY last_name"
        c.execute(query, params)
        result = [dict(row) for row in c.fetchall()]
        conn.close()
        return result
    
    def delete(self, contact_id):
        # Delete contact by ID
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        deleted = c.rowcount > 0
        conn.close()
        return deleted, "Deleted" if deleted else "Not found"
    
    def update(self, contact_id, updates):
        # Update contact info
        if not updates:
            return False, "No updates"
        
        conn = self._get_conn()
        c = conn.cursor()
        
        valid = ['first_name', 'last_name', 'group_name', 'position', 'email', 'phone', 'photo_path']
        set_parts = []
        values = []
        
        for field, value in updates.items():
            if field in valid:
                set_parts.append(f"{field} = ?")
                values.append(value)
        
        if not set_parts:
            return False, "No valid fields"
        
        values.append(contact_id)
        query = f"UPDATE contacts SET {', '.join(set_parts)} WHERE id = ?"
        
        try:
            c.execute(query, values)
            conn.commit()
            updated = c.rowcount > 0
            return updated, "Updated" if updated else "Not found"
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()


# Helper to show all contacts
def show_all(db, title):
    print(f"\n{title}")
    print("-" * 70)
    contacts = db.get_all()
    if not contacts:
        print("No contacts in database")
        return
    
    print(f"Total: {len(contacts)} contacts")
    print(f"{'ID':<3} | {'Name':<20} | {'Group':<15} | {'Phone':<12} | {'Position':<15}")
    print("-" * 70)
    for c in contacts:
        name = f"{c['first_name']} {c['last_name']}"
        print(f"{c['id']:<3} | {name:<20} | {c['group_name']:<15} | {c['phone']:<12} | {c.get('position', '-'):<15}")


# Test all functions
def test_all():
    print("=== Testing all DB functions ===")
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    test_db_path = os.path.join(project_dir, "test.db")
    
    # Clean old test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = PhoneBookDB("test.db")  
    
    # 1. Start with empty DB
    show_all(db, "1. EMPTY DATABASE (START)")
    
    # 2. Add 3 contacts
    print("\n\n2. ADDING 3 CONTACTS")
    print("-" * 70)
    contacts = [
        {'first_name': 'Ali', 'last_name': 'Ahmadi', 'group_name': 'IT', 'phone': '09121234567', 'position': 'Developer'},
        {'first_name': 'Sarah', 'last_name': 'Khosh', 'group_name': 'Software', 'phone': '09129876543', 'position': 'Manager'},
        {'first_name': 'Hesam', 'last_name': 'Mohammadi', 'group_name': 'IT', 'phone': '09127778899', 'position': 'Team Lead'}
    ]
    
    for c in contacts:
        ok, msg = db.add_contact(c)
        print(f"Added: {c['first_name']} {c['last_name']} - {msg}")
    
    show_all(db, "3. AFTER ADDING 3 CONTACTS")
    
    # 3. Update contacts
    print("\n\n4. UPDATING CONTACTS")
    print("-" * 70)
    # Update Ali
    ok, msg = db.update(1, {'position': 'Senior', 'email': 'Ali@email.com'})
    print(f"Update ID 1 (Ali): {msg}")
    
    # Update Hesam
    ok, msg = db.update(3, {'group_name': 'Computer', 'phone': '09129998877'})
    print(f"Update ID 3 (Hesam): {msg}")
    
    show_all(db, "5. AFTER UPDATES")
    
    # 4. Delete contact
    print("\n\n6. DELETING CONTACT")
    print("-" * 70)
    ok, msg = db.delete(2)
    print(f"Delete ID 2 (Sarah): {msg}")
    
    show_all(db, "7. AFTER DELETE (2 contacts left)")
    
    # 5. Search tests
    print("\n\n8. SEARCH TESTS")
    print("-" * 70)
    
    # Search IT group
    print("a) Search 'IT' group:")
    results = db.search({'group_name': 'IT'})
    for r in results:
        print(f"   - {r['first_name']} {r['last_name']}")
    
    # Search Computer group
    print("\nb) Search 'Computer' group:")
    results = db.search({'group_name': 'Computer'})
    for r in results:
        print(f"   - {r['first_name']} {r['last_name']}")
    
    # Search by name
    print("\nc) Search name 'Ali':")
    results = db.search({'first_name': 'Ali'})
    for r in results:
        print(f"   - {r['first_name']} {r['last_name']} ({r['phone']})")
    
    # Combined search
    print("\nd) Search IT + phone 0912:")
    results = db.search({'group_name': 'IT', 'phone': '0912'})
    for r in results:
        print(f"   - {r['first_name']} {r['last_name']}")
    
    # 6. Final state
    show_all(db, "9. FINAL DATABASE STATE")
    
    print(f"\n✓ Database files created in project folder: {project_dir}")
    print(f"  - phonebook.db (main database)")
    print(f"  - test.db (test database)")

# Run test
if __name__ == "__main__":

    test_all()
