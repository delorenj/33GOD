from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

class Store:
    def __init__(self, dsn):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def migrate(self):
        with self.connect() as conn:
            for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                with conn.transaction():
                    conn.execute(path.read_text())

    @contextmanager
    def board_lock(self, project_id):
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (project_id,))
            try:
                yield conn
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (project_id,))

    def board(self, conn, project):
        conn.execute("INSERT INTO krebs.boards(project_id,board_id) VALUES(%s,%s) ON CONFLICT(project_id) DO NOTHING", (project["project_id"], project["board"]))
        row = conn.execute("SELECT * FROM krebs.boards WHERE project_id=%s", (project["project_id"],)).fetchone()
        if row["board_id"] != project["board"]:
            raise ValueError("board binding changed; pause and reconcile before activation")
        return dict(row)

    def save(self, conn, state):
        conn.execute("UPDATE krebs.boards SET revision=%s,generation=%s,active=%s,tickets=%s,pending=%s,used_runs=%s WHERE project_id=%s", (state["revision"], state["generation"], Jsonb(state["active"]), Jsonb(state["tickets"]), state.get("pending"), Jsonb(state.get("used_runs",[])), state["project_id"]))
