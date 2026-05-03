"""
数据库操作模块 (SQLite)
- 错题本 CRUD
- 学习统计
- 题库管理
- 学习进度管理
"""
import sqlite3
import json
import hashlib
import time
import pandas as pd
from datetime import datetime
import streamlit as st

DB_FILE = 'quiz.db'


# ============================================================
# 数据库初始化
# ============================================================

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS wrong_book
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT,
                  question_type TEXT,
                  full_data TEXT,
                  file_name TEXT,
                  error_count INTEGER DEFAULT 1,
                  first_wrong_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_wrong_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  added_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS study_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date DATE DEFAULT CURRENT_DATE,
                  total_questions INTEGER,
                  correct_answers INTEGER,
                  total_time INTEGER,
                  accuracy REAL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS question_banks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bank_name TEXT NOT NULL,
                  file_name TEXT,
                  file_hash TEXT UNIQUE,
                  total_questions INTEGER,
                  question_types TEXT,
                  import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_used_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_active INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS bank_questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bank_id INTEGER,
                  question_hash TEXT,
                  question_data TEXT,
                  FOREIGN KEY (bank_id) REFERENCES question_banks(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS study_progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bank_id INTEGER,
                  practice_mode TEXT,
                  current_index INTEGER DEFAULT 0,
                  question_results TEXT,
                  start_time TIMESTAMP,
                  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_completed INTEGER DEFAULT 0,
                  total_questions INTEGER,
                  FOREIGN KEY (bank_id) REFERENCES question_banks(id) ON DELETE CASCADE)''')

    def add_column_if_not_exists(table_name, column_name, column_type):
        try:
            c.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
        except sqlite3.OperationalError:
            try:
                c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"已添加列 {table_name}.{column_name}")
            except Exception as e:
                print(f"添加列 {column_name} 失败: {e}")

    add_column_if_not_exists('wrong_book', 'file_name', 'TEXT')
    add_column_if_not_exists('wrong_book', 'error_count', 'INTEGER DEFAULT 1')
    add_column_if_not_exists('wrong_book', 'first_wrong_time', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    add_column_if_not_exists('wrong_book', 'last_wrong_time', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

    c.execute("CREATE INDEX IF NOT EXISTS idx_question ON wrong_book(question)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_date ON study_stats(date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_file_name ON wrong_book(file_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bank_hash ON question_banks(file_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bank_active ON question_banks(is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_question_bank ON bank_questions(bank_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_question_hash ON bank_questions(question_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_progress_bank ON study_progress(bank_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_progress_completed ON study_progress(is_completed)")

    conn.commit()
    conn.close()

    verify_db_structure()


def verify_db_structure():
    """验证数据库表结构完整性"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("PRAGMA table_info(wrong_book)")
        columns = [col[1] for col in c.fetchall()]

        required_columns = ['id', 'question', 'question_type', 'full_data', 'file_name',
                            'error_count', 'first_wrong_time', 'last_wrong_time', 'added_time']

        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"数据库表结构不完整，缺失列: {missing_columns}")
            for col in missing_columns:
                if col == 'error_count':
                    c.execute("ALTER TABLE wrong_book ADD COLUMN error_count INTEGER DEFAULT 1")
                elif col in ['first_wrong_time', 'last_wrong_time', 'added_time']:
                    c.execute(f"ALTER TABLE wrong_book ADD COLUMN {col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                elif col == 'file_name':
                    c.execute("ALTER TABLE wrong_book ADD COLUMN file_name TEXT")

        conn.commit()
        return len(missing_columns) == 0
    except Exception as e:
        print(f"数据库结构验证失败: {e}")
        return False
    finally:
        conn.close()


# ============================================================
# 错题本操作
# ============================================================

def add_to_wrong_book(row, file_name=None):
    """添加错题到数据库 (更新错误次数而非重复添加)"""
    question_text = row.get('题目', '')
    if not question_text:
        return False

    actual_file_name = file_name

    if st.session_state.get('review_mode', False) and '_file_name' in row:
        actual_file_name = row.get('_file_name', file_name)
    elif '_file_name' in row and row['_file_name']:
        actual_file_name = row.get('_file_name')

    if actual_file_name == "错题本" and '_original_file_name' in row:
        actual_file_name = row.get('_original_file_name', file_name)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        if actual_file_name:
            c.execute("""
                SELECT id, error_count FROM wrong_book
                WHERE question = ? AND file_name = ?
            """, (question_text, actual_file_name))
        else:
            c.execute("""
                SELECT id, error_count FROM wrong_book
                WHERE question = ? AND (file_name IS NULL OR file_name = '')
            """, (question_text,))

        exists = c.fetchone()

        if not exists:
            row_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
            row_json = json.dumps(row_dict, ensure_ascii=False)

            if '_original_file_name' in row:
                actual_file_name = row['_original_file_name']

            c.execute("""
                INSERT INTO wrong_book
                (question, question_type, full_data, file_name,
                 error_count, first_wrong_time, last_wrong_time)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (question_text, row.get('题型', '未知'), row_json, actual_file_name))
            conn.commit()
            return True
        else:
            q_id, error_count = exists
            c.execute("""
                UPDATE wrong_book
                SET error_count = ?, last_wrong_time = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (error_count + 1, q_id))
            conn.commit()
            return False
    except Exception as e:
        print(f"添加错题失败: {e}")
        return False
    finally:
        conn.close()


def get_wrong_questions(limit: int = 100, file_filter: str = None,
                        sort_by: str = 'error_count',
                        error_count_filter: tuple = None):
    """获取所有错题"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        conditions = []
        params = []

        if file_filter:
            conditions.append("file_name = ?")
            params.append(file_filter)

        if error_count_filter:
            min_errors, max_errors = error_count_filter
            conditions.append("error_count >= ? AND error_count <= ?")
            params.extend([min_errors, max_errors])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        order_map = {
            'error_count': "error_count DESC, last_wrong_time DESC",
            'recent': "last_wrong_time DESC",
            'first_wrong': "first_wrong_time ASC",
            'error_count_random': "error_count DESC, RANDOM()",
            'recent_random': "last_wrong_time DESC, RANDOM()",
            'random': "RANDOM()",
        }
        order_by = order_map.get(sort_by, "error_count DESC, last_wrong_time DESC")

        query = f"""
            SELECT id, full_data, file_name, added_time,
                   error_count, first_wrong_time, last_wrong_time
            FROM wrong_book
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT ?
        """

        params.append(limit)
        c.execute(query, params)
        rows = c.fetchall()

        data_list = []
        for r in rows:
            q_id = r[0]
            q_data = json.loads(r[1])
            q_data['_db_id'] = q_id
            q_data['_file_name'] = r[2]
            q_data['_added_time'] = r[3]
            q_data['_error_count'] = r[4]
            q_data['_first_wrong_time'] = r[5]
            q_data['_last_wrong_time'] = r[6]
            data_list.append(q_data)

        return data_list
    except Exception as e:
        print(f"获取错题失败: {e}")
        return []
    finally:
        conn.close()


def get_wrong_book_files():
    """获取错题本中所有不同的文件名"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT DISTINCT file_name FROM wrong_book
            WHERE file_name IS NOT NULL
            AND file_name != ''
            AND file_name != '错题本'
            ORDER BY file_name
        """)
        rows = c.fetchall()
        return [row[0] for row in rows if row[0]]
    except Exception as e:
        print(f"获取错题本文件列表失败: {e}")
        return []
    finally:
        conn.close()


def delete_wrong_question(q_id: int) -> bool:
    """根据ID删除错题"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("DELETE FROM wrong_book WHERE id = ?", (q_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"删除错题失败: {e}")
        return False
    finally:
        conn.close()


def clear_wrong_book(file_name: str = None) -> bool:
    """清空错题本"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        if file_name:
            c.execute("DELETE FROM wrong_book WHERE file_name = ?", (file_name,))
        else:
            c.execute("DELETE FROM wrong_book")
        conn.commit()
        return True
    except Exception as e:
        print(f"清空错题本失败: {e}")
        return False
    finally:
        conn.close()


def clear_wrong_book_by_filter(file_filter: str = None, question_types=None):
    """按筛选条件清空错题本"""
    if question_types is None:
        question_types = []
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        conditions = []
        params = []

        if file_filter and file_filter != '全部':
            conditions.append("file_name = ?")
            params.append(file_filter)

        if question_types:
            query = "SELECT id, full_data FROM wrong_book"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            c.execute(query, params)
            rows = c.fetchall()

            delete_ids = []
            for r in rows:
                q_id = r[0]
                q_data = json.loads(r[1])
                q_type = q_data.get('题型', '')
                if q_type in question_types:
                    delete_ids.append(q_id)

            if delete_ids:
                placeholders = ','.join(['?'] * len(delete_ids))
                c.execute(f"DELETE FROM wrong_book WHERE id IN ({placeholders})", delete_ids)
                conn.commit()
                return len(delete_ids)
            else:
                return 0
        else:
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"DELETE FROM wrong_book WHERE {where_clause}"
            c.execute(query, params)
            conn.commit()
            return c.rowcount
    except Exception as e:
        print(f"按筛选条件清空错题本失败: {e}")
        return 0
    finally:
        conn.close()


# ============================================================
# 学习统计
# ============================================================

def save_study_stats(total_questions: int, correct_answers: int, total_time: int):
    """保存学习统计数据"""
    if total_questions == 0:
        return

    accuracy = correct_answers / total_questions * 100 if total_questions > 0 else 0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT OR REPLACE INTO study_stats (date, total_questions, correct_answers, total_time, accuracy)
            VALUES (DATE('now'), ?, ?, ?, ?)
        """, (total_questions, correct_answers, total_time, accuracy))
        conn.commit()
    except Exception as e:
        print(f"保存学习统计失败: {e}")
    finally:
        conn.close()


def calculate_total_time():
    """统一计算总时长"""
    total_time = 0

    if hasattr(st.session_state, 'final_quiz_time') and st.session_state.final_quiz_time:
        total_time = st.session_state.final_quiz_time
    elif hasattr(st.session_state, 'quiz_start_time') and st.session_state.quiz_start_time:
        if hasattr(st.session_state, 'quiz_end_time') and st.session_state.quiz_end_time:
            total_time = st.session_state.quiz_end_time - st.session_state.quiz_start_time
        else:
            total_time = time.time() - st.session_state.quiz_start_time
    elif hasattr(st.session_state, 'question_results') and st.session_state.question_results:
        total_time = sum(r.get('time', 0) for r in st.session_state.question_results)

    return total_time


def save_study_stats_with_consistent_time(total_questions, correct_answers):
    """使用统一的时间计算方法保存学习统计"""
    total_time = calculate_total_time()
    save_study_stats(total_questions, correct_answers, int(total_time))


def get_study_history(days: int = 7):
    """获取学习历史数据"""
    conn = sqlite3.connect(DB_FILE)

    try:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_stats'")
        if not c.fetchone():
            return pd.DataFrame()

        query = """
            SELECT date, total_questions, correct_answers, total_time, accuracy
            FROM study_stats
            WHERE date >= DATE('now', ?)
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(f'-{days} days',))
        return df
    except Exception as e:
        print(f"获取学习历史失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_daily_summary():
    """获取每日学习汇总数据"""
    conn = sqlite3.connect(DB_FILE)

    try:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_stats'")
        if not c.fetchone():
            return pd.DataFrame()

        query = """
            SELECT date,
                   SUM(total_questions) as total_questions,
                   SUM(correct_answers) as correct_answers,
                   SUM(total_time) as total_time,
                   AVG(accuracy) as accuracy
            FROM study_stats
            WHERE date >= DATE('now', '-30 days')
            GROUP BY date
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn)

        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        return df
    except Exception as e:
        print(f"获取每日汇总失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


# ============================================================
# 题库管理
# ============================================================

def calculate_file_hash(df):
    """计算DataFrame的哈希值"""
    df_string = df.to_csv(index=False).encode('utf-8')
    return hashlib.md5(df_string).hexdigest()


def save_question_bank(df, file_name, bank_name=None):
    """保存题库到数据库"""
    if df is None or df.empty:
        return None

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        file_hash = calculate_file_hash(df)

        c.execute("SELECT id FROM question_banks WHERE file_hash = ?", (file_hash,))
        exists = c.fetchone()

        if exists:
            c.execute("UPDATE question_banks SET last_used_time = CURRENT_TIMESTAMP WHERE id = ?", (exists[0],))
            conn.commit()
            return exists[0]

        type_counts = {}
        if '题型' in df.columns:
            for q_type, count in df['题型'].value_counts().items():
                type_counts[q_type] = count

        if not bank_name:
            bank_name = file_name.split('.')[0]

        c.execute("""
            INSERT INTO question_banks
            (bank_name, file_name, file_hash, total_questions, question_types, is_active)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (bank_name, file_name, file_hash, len(df), json.dumps(type_counts)))

        bank_id = c.lastrowid

        for _, row in df.iterrows():
            question_hash = hashlib.md5(str(row.get('题目', '')).encode('utf-8')).hexdigest()
            question_data = json.dumps(row.to_dict(), ensure_ascii=False)
            c.execute("""
                INSERT INTO bank_questions (bank_id, question_hash, question_data)
                VALUES (?, ?, ?)
            """, (bank_id, question_hash, question_data))

        conn.commit()
        return bank_id
    except Exception as e:
        print(f"保存题库失败: {e}")
        return None
    finally:
        conn.close()


def get_all_question_banks():
    """获取所有题库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT id, bank_name, file_name, total_questions,
                   question_types, import_time, last_used_time, is_active
            FROM question_banks
            ORDER BY last_used_time DESC
        """)

        rows = c.fetchall()
        banks = []
        for r in rows:
            banks.append({
                'id': r[0],
                'bank_name': r[1],
                'file_name': r[2],
                'total_questions': r[3],
                'question_types': json.loads(r[4]) if r[4] else {},
                'import_time': r[5],
                'last_used_time': r[6],
                'is_active': r[7]
            })
        return banks
    except Exception as e:
        print(f"获取题库失败: {e}")
        return []
    finally:
        conn.close()


def activate_question_bank(bank_id):
    """激活指定题库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("UPDATE question_banks SET is_active = 0")
        c.execute("UPDATE question_banks SET is_active = 1, last_used_time = CURRENT_TIMESTAMP WHERE id = ?",
                  (bank_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"激活题库失败: {e}")
        return False
    finally:
        conn.close()


def get_active_question_bank():
    """获取当前激活的题库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT id, bank_name, file_name, total_questions, question_types
            FROM question_banks
            WHERE is_active = 1
            LIMIT 1
        """)

        row = c.fetchone()
        if row:
            return {
                'id': row[0],
                'bank_name': row[1],
                'file_name': row[2],
                'total_questions': row[3],
                'question_types': json.loads(row[4]) if row[4] else {}
            }
        return None
    except Exception as e:
        print(f"获取激活题库失败: {e}")
        return None
    finally:
        conn.close()


def load_questions_from_bank(bank_id):
    """从题库加载题目"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("SELECT question_data FROM bank_questions WHERE bank_id = ?", (bank_id,))
        rows = c.fetchall()
        questions = []
        for r in rows:
            questions.append(json.loads(r[0]))
        return pd.DataFrame(questions)
    except Exception as e:
        print(f"加载题库题目失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def delete_question_bank(bank_id):
    """删除题库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("SELECT is_active FROM question_banks WHERE id = ?", (bank_id,))
        row = c.fetchone()
        if row and row[0] == 1:
            st.error("无法删除当前正在使用的题库")
            return False

        c.execute("DELETE FROM question_banks WHERE id = ?", (bank_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"删除题库失败: {e}")
        return False
    finally:
        conn.close()


# ============================================================
# 学习进度管理
# ============================================================

def save_study_progress(bank_id, practice_mode, current_index, question_results, total_questions, is_completed=False):
    """保存学习进度"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT id FROM study_progress
            WHERE bank_id = ? AND practice_mode = ? AND is_completed = 0
        """, (bank_id, practice_mode))

        existing = c.fetchone()

        if existing:
            c.execute("""
                UPDATE study_progress
                SET current_index = ?, question_results = ?, last_update = CURRENT_TIMESTAMP,
                    is_completed = ?, total_questions = ?
                WHERE id = ?
            """, (current_index, json.dumps(question_results), 1 if is_completed else 0, total_questions, existing[0]))
        else:
            c.execute("""
                INSERT INTO study_progress
                (bank_id, practice_mode, current_index, question_results, start_time, total_questions, is_completed)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, (bank_id, practice_mode, current_index, json.dumps(question_results), total_questions,
                  1 if is_completed else 0))

        conn.commit()
        return True
    except Exception as e:
        print(f"保存学习进度失败: {e}")
        return False
    finally:
        conn.close()


def get_study_progress(bank_id, practice_mode):
    """获取学习进度"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT id, current_index, question_results, start_time, total_questions
            FROM study_progress
            WHERE bank_id = ? AND practice_mode = ? AND is_completed = 0
            ORDER BY last_update DESC
            LIMIT 1
        """, (bank_id, practice_mode))

        row = c.fetchone()
        if row:
            progress_id, current_index, question_results_json, start_time, total_questions = row
            question_results = json.loads(question_results_json) if question_results_json else []
            return {
                'id': progress_id,
                'current_index': current_index,
                'question_results': question_results,
                'start_time': start_time,
                'total_questions': total_questions
            }
        return None
    except Exception as e:
        print(f"获取学习进度失败: {e}")
        return None
    finally:
        conn.close()


def get_all_study_progress():
    """获取所有未完成的学习进度"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            SELECT sp.id, sp.bank_id, sp.practice_mode, sp.current_index,
                   sp.total_questions, sp.start_time, sp.last_update,
                   sp.question_results,
                   qb.bank_name, qb.file_name
            FROM study_progress sp
            JOIN question_banks qb ON sp.bank_id = qb.id
            WHERE sp.is_completed = 0
            ORDER BY sp.last_update DESC
        """)

        rows = c.fetchall()
        progress_list = []
        for r in rows:
            progress_list.append({
                'id': r[0],
                'bank_id': r[1],
                'practice_mode': r[2],
                'current_index': r[3],
                'total_questions': r[4],
                'start_time': r[5],
                'last_update': r[6],
                'question_results': json.loads(r[7]) if r[7] else [],
                'bank_name': r[8],
                'file_name': r[9]
            })
        return progress_list
    except Exception as e:
        print(f"获取所有学习进度失败: {e}")
        return []
    finally:
        conn.close()


def mark_progress_completed(progress_id):
    """标记进度为已完成"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            UPDATE study_progress
            SET is_completed = 1, last_update = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (progress_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"标记进度完成失败: {e}")
        return False
    finally:
        conn.close()


def delete_study_progress(progress_id):
    """删除学习进度"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("DELETE FROM study_progress WHERE id = ?", (progress_id,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"删除学习进度失败: {e}")
        return False
    finally:
        conn.close()
