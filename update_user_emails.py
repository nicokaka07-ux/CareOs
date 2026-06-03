import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM accounts_staffuser")
print('total users:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM accounts_staffuser WHERE email IS NULL OR email = ''")
blank_count = c.fetchone()[0]
print('blank or null emails:', blank_count)

c.execute("UPDATE accounts_staffuser SET email = 'careos903@gmail.com'")
conn.commit()
print('updated rows:', c.rowcount)

c.execute("SELECT COUNT(*) FROM accounts_staffuser WHERE email = 'careos903@gmail.com'")
print('careos903@gmail.com users:', c.fetchone()[0])

conn.close()
