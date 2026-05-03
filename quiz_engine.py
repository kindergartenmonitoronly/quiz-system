"""
核心答题逻辑
- 计时器
- 答题流程控制
- 导航辅助
- 状态同步
"""
import time
import json
import random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from database import (
    add_to_wrong_book, save_study_progress, get_wrong_questions,
    get_active_question_bank
)
from utils import generate_random_indices


# ============================================================
# 导航辅助函数
# ============================================================

def is_question_answered(question_index):
    """检查指定索引的题目是否已经答题"""
    for result in st.session_state.question_results:
        if result['index'] == question_index:
            return True, result
    return False, None


def get_original_question_index(result_index):
    """根据结果索引获取原始题目索引"""
    if hasattr(st.session_state, 'random_mode') and st.session_state.random_mode:
        if hasattr(st.session_state, 'random_indices') and result_index < len(st.session_state.random_indices):
            return st.session_state.random_indices[result_index]
    elif hasattr(st.session_state, 'quiz_queue_indices') and st.session_state.quiz_queue_indices:
        if result_index < len(st.session_state.quiz_queue_indices):
            return st.session_state.quiz_queue_indices[result_index]
    return result_index


def get_current_question_and_total():
    """获取当前题目和总题数"""
    if st.session_state.data is None:
        return None, 0

    df = st.session_state.data

    if st.session_state.random_mode:
        if not hasattr(st.session_state, 'random_indices') or st.session_state.current_index >= len(
                st.session_state.random_indices):
            return None, 0

        curr_idx = st.session_state.random_indices[st.session_state.current_index]
        row = df.loc[curr_idx]
        total_q = len(st.session_state.random_indices)

    elif st.session_state.review_mode:
        if st.session_state.current_index >= len(df):
            return None, 0

        row = df.iloc[st.session_state.current_index]
        total_q = len(df)

    else:
        if hasattr(st.session_state, 'quiz_queue_indices') and st.session_state.quiz_queue_indices:
            if st.session_state.current_index >= len(st.session_state.quiz_queue_indices):
                st.session_state.current_index = len(st.session_state.quiz_queue_indices) - 1

            original_idx = st.session_state.quiz_queue_indices[st.session_state.current_index]
            row = df.loc[original_idx]
            total_q = len(st.session_state.quiz_queue_indices)
        else:
            if st.session_state.current_index >= len(df):
                return None, 0

            row = df.iloc[st.session_state.current_index]
            total_q = len(df)

    return row, total_q


def update_multiple_choice_answer():
    """更新多选题的用户答案（基于checkbox状态）"""
    selected_letters = []
    for i in range(6):
        letter = chr(65 + i)
        key = f"mq_{letter}_{st.session_state.current_index}"
        if st.session_state.get(key, False):
            selected_letters.append(letter)

    st.session_state.user_answer = ''.join(sorted(selected_letters))


# ============================================================
# 计时器
# ============================================================

def start_question_timer():
    """开始当前题目的计时"""
    st.session_state.question_start_time = time.time()
    st.session_state.auto_timeout = False


def check_timeout_logic():
    """后端检查是否超时"""
    if (st.session_state.question_start_time and
            st.session_state.quiz_active and
            not st.session_state.show_result):

        elapsed = time.time() - st.session_state.question_start_time
        if elapsed > (st.session_state.time_limit + 1.5):
            st.session_state.auto_timeout = True
            return True
    return False


def render_js_timer():
    """渲染JS倒计时组件"""
    if not st.session_state.quiz_active or st.session_state.show_result:
        return

    if not hasattr(st.session_state, 'question_start_time') or st.session_state.question_start_time is None:
        start_question_timer()
        return

    end_time = st.session_state.question_start_time + st.session_state.time_limit

    js = f"""
    <div id="timer_box" style="
        font-size: 18px; font-weight: bold;
        background: #e8f5e9; border: 2px solid #4CAF50;
        padding: 8px 16px; border-radius: 8px; text-align: center;
        width: 100%; white-space: nowrap;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        ⏱️ 加载中...
    </div>
    <script>
    (function() {{
        var endTime = {end_time};
        var timerDiv = document.getElementById("timer_box");

        function updateTimer() {{
            var now = new Date().getTime() / 1000;
            var left = Math.max(0, endTime - now);

            if (left <= 0) {{
                timerDiv.innerHTML = "⚠️ 时间到！";
                timerDiv.style.color = "white";
                timerDiv.style.background = "#f44336";
                timerDiv.style.borderColor = "#d32f2f";
                // 找到提交答案按钮（主按钮，文本包含"提交答案"）
                setTimeout(() => {{
                    var buttons = document.querySelectorAll('button[kind="primary"]');
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText && buttons[i].innerText.includes('提交答案')) {{
                            buttons[i].click();
                            break;
                        }}
                    }}
                }}, 800);
                return;
            }}

            var minutes = Math.floor(left / 60);
            var seconds = Math.floor(left % 60);

            if (minutes > 0) {{
                timerDiv.innerHTML = "⏱️ " + minutes + "分" + seconds + "秒";
            }} else {{
                timerDiv.innerHTML = "⏱️ " + seconds + "秒";
            }}

            if (left <= 10) {{
                timerDiv.style.color = "#ff5722";
                timerDiv.style.background = "#fff3e0";
                timerDiv.style.borderColor = "#ff9800";
            }}

            if (left <= 5) {{
                timerDiv.style.color = "#f44336";
                timerDiv.style.background = "#ffebee";
                timerDiv.style.borderColor = "#f44336";
            }}

            requestAnimationFrame(updateTimer);
        }}
        updateTimer();
    }})();
    </script>
    """
    components.html(js, height=60)


# ============================================================
# 核心流程控制
# ============================================================

def start_quiz(mode, continue_progress=False, progress_data=None):
    """通用的开始刷题入口"""
    if st.session_state.data is None and not continue_progress:
        st.error("请先导入题库")
        return

    st.session_state.current_index = 0
    st.session_state.show_result = False
    st.session_state.user_answer = None
    st.session_state.question_results = []
    st.session_state.quiz_completed = False
    st.session_state.quiz_active = True
    st.session_state.quiz_start_time = time.time()
    st.session_state.auto_timeout = False
    st.session_state.force_exit_results = False
    st.session_state.show_answer_card = False
    st.session_state.jump_to_question = None
    st.session_state.show_answer_card_detail = False
    st.session_state.celebration_shown = False
    st.session_state.question_start_time = time.time()
    st.session_state.quiz_end_time = None

    if continue_progress and progress_data:
        st.session_state.current_index = progress_data.get('current_index', 0)
        question_results_json = progress_data.get('question_results', [])
        if isinstance(question_results_json, str):
            try:
                st.session_state.question_results = json.loads(question_results_json)
            except:
                st.session_state.question_results = []
        else:
            st.session_state.question_results = question_results_json

        # 恢复原题目数量设置
        saved_total = progress_data.get('total_questions', 0)
        if saved_total > 0:
            st.session_state.question_count = saved_total

        if progress_data.get('practice_mode') == 'review':
            st.session_state.review_mode = True
            st.session_state.current_file_name = "错题重练"
            st.session_state.current_bank_name = "错题重练"
        elif progress_data.get('practice_mode') == 'random':
            st.session_state.random_mode = True
            st.session_state.review_mode = False
        elif progress_data.get('practice_mode') == 'sequential':
            st.session_state.random_mode = False
            st.session_state.review_mode = False
            # 顺序模式：重建索引队列（使用保存的题目数）
            df = st.session_state.data
            if not st.session_state.selected_types:
                filtered_df = df
            else:
                filtered_df = df[df['题型'].isin(st.session_state.selected_types)]
            quiz_indices = filtered_df.index.tolist()[:saved_total] if saved_total else filtered_df.index.tolist()
            st.session_state.quiz_queue_indices = quiz_indices
            st.session_state.random_indices = []

        st.session_state.question_start_time = time.time()
        st.success(
            f"已加载上次进度: 已完成 {progress_data.get('current_index', 0)}/{saved_total} 题")

        st.session_state.sidebar_collapsed = True
        start_question_timer()
        return

    elif mode == 'review':
        st.session_state.review_mode = True

        wrong_list = get_wrong_questions()

        filtered_wrong_list = []
        for wrong in wrong_list:
            q_type = wrong.get('题型', '')
            if st.session_state.selected_types and q_type not in st.session_state.selected_types:
                continue

            file_name = wrong.get('_file_name', '')
            if (hasattr(st.session_state, 'wrong_book_filter') and
                    st.session_state.wrong_book_filter and
                    st.session_state.wrong_book_filter != '全部' and
                    file_name != st.session_state.wrong_book_filter):
                continue

            wrong['_original_file_name'] = file_name
            filtered_wrong_list.append(wrong)

        if not filtered_wrong_list:
            st.error("没有符合条件的错题")
            st.session_state.quiz_active = False
            return

        wrong_df = pd.DataFrame(filtered_wrong_list)
        st.session_state.data = wrong_df
        st.session_state.current_file_name = "错题重练"
        st.session_state.current_bank_name = "错题重练"

        if st.session_state.wrong_book_random_mode:
            st.session_state.random_mode = True
            indices = list(range(len(wrong_df)))
            if len(indices) > st.session_state.question_count:
                indices = random.sample(indices, st.session_state.question_count)
            random.shuffle(indices)
            st.session_state.random_indices = indices
        else:
            st.session_state.random_mode = False
            st.session_state.random_indices = []

        if not st.session_state.original_bank_before_review:
            active_bank = get_active_question_bank()
            if active_bank:
                st.session_state.original_bank_before_review = {
                    'id': active_bank['id'],
                    'name': active_bank['bank_name'],
                    'file': active_bank['file_name']
                }

    elif mode == 'random':
        st.session_state.random_mode = True
        st.session_state.review_mode = False
        df = st.session_state.data

        if not hasattr(st.session_state, 'original_data_backup'):
            st.session_state.original_data_backup = df.copy()

        indices = generate_random_indices(
            df,
            st.session_state.question_count,
            st.session_state.selected_types
        )
        st.session_state.random_indices = indices

        if not indices:
            st.error("未找到符合条件的题目")
            st.session_state.quiz_active = False
            return

    elif mode == 'sequential':
        st.session_state.random_mode = False
        st.session_state.review_mode = False
        st.session_state.practice_mode = 'sequential'

        df = st.session_state.data

        if not hasattr(st.session_state, 'original_data_backup'):
            st.session_state.original_data_backup = df.copy()

        if not st.session_state.selected_types:
            filtered_df = df
        else:
            filtered_df = df[df['题型'].isin(st.session_state.selected_types)]

        if len(filtered_df) == 0:
            st.error("未找到符合条件的题目")
            st.session_state.quiz_active = False
            return

        quiz_indices = filtered_df.index.tolist()
        target_count = st.session_state.get('question_count', len(quiz_indices))

        if not hasattr(st.session_state, 'question_count'):
            st.session_state.question_count = len(quiz_indices)
        elif st.session_state.question_count > len(quiz_indices):
            st.session_state.question_count = len(quiz_indices)

        if st.session_state.question_count < len(quiz_indices):
            quiz_indices = quiz_indices[:st.session_state.question_count]

        st.session_state.quiz_queue_indices = quiz_indices
        st.session_state.random_indices = []

    st.session_state.sidebar_collapsed = True
    start_question_timer()


def submit_answer_action(row):
    """提交答案处理"""
    is_timeout = check_timeout_logic()
    user_ans = st.session_state.user_answer

    if is_timeout:
        user_ans = user_ans if user_ans else "超时未答"
        st.session_state.auto_timeout = True

    if not user_ans and not is_timeout:
        st.warning("请选择或填写答案")
        return

    st.session_state.show_result = True

    correct_ans = str(row['答案']).strip()
    is_correct = False

    if is_timeout:
        is_correct = False
    else:
        if row.get('题型') == '多选题':
            is_correct = (''.join(sorted(str(user_ans))) == ''.join(sorted(correct_ans)))
        else:
            is_correct = (str(user_ans).upper() == correct_ans.upper())

    time_spent = time.time() - st.session_state.question_start_time
    st.session_state.question_results.append({
        'index': st.session_state.current_index,
        'question': row['题目'],
        'user': user_ans,
        'correct': correct_ans,
        'is_correct': is_correct,
        'time': round(min(time_spent, st.session_state.time_limit), 1)
    })

    if not is_correct:
        add_to_wrong_book(row, st.session_state.current_file_name)

    if st.session_state.current_bank_id and st.session_state.practice_mode:
        save_study_progress(
            bank_id=st.session_state.current_bank_id,
            practice_mode=st.session_state.practice_mode,
            current_index=st.session_state.current_index,
            question_results=st.session_state.question_results,
            total_questions=get_total_questions()
        )


def restore_original_data():
    """恢复原始题库数据"""
    if hasattr(st.session_state, 'original_data_backup'):
        st.session_state.data = st.session_state.original_data_backup
        del st.session_state.original_data_backup

    if hasattr(st.session_state, 'quiz_queue_indices'):
        del st.session_state.quiz_queue_indices


def get_total_questions():
    """统一获取当前刷题的总题目数"""
    if st.session_state.random_mode and st.session_state.random_indices:
        return len(st.session_state.random_indices)
    if (hasattr(st.session_state, 'quiz_queue_indices')
            and st.session_state.quiz_queue_indices):
        return len(st.session_state.quiz_queue_indices)
    if st.session_state.data is not None:
        return len(st.session_state.data)
    return 0
