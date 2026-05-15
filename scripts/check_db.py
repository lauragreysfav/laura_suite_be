import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")).fetchall()
print('Tables in database:')
for t in tables:
    print(f'  - {t[0]}')
for tbl in ['stashdb_cache_performers', 'stashdb_cache_studios', 'stashdb_cache_scenes']:
    try:
        cols = db.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}' ORDER BY ordinal_position")).fetchall()
        print(f'\n{tbl} columns:')
        for c in cols:
            print(f'  - {c[0]}')
        cnt = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
        print(f'  row count: {cnt}')
    except Exception as e:
        print(f'\n{tbl} ERROR: {e}')
db.close()
