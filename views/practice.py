"""刷题页面及设置"""
import streamlit as st
import pandas as pd
import time
import streamlit.components.v1 as components

from database import (
    get_all_question_banks, get_active_question_bank, load_questions_from_bank,
    activate_question_bank, get_wrong_book_files, get_wrong_questions
)
from quiz_engine import start_quiz
from utils import truncate_filename


def render_practice_page():
    """渲染刷题页面"""
    progress_list = __import__('database', fromlist=['get_all_study_progress']).get_all_study_progress()
    has_progress = len(progress_list) > 0

    if has_progress and not st.session_state.continue_progress:
        st.info(f"📋 您有 {len(progress_list)} 个未完成的刷题进度")
        if st.button("查看并继续上次进度", type="primary"):
            st.session_state.current_page = 'progress'
            st.rerun()
        st.divider()

    if st.session_state.data is None:
        active_bank = get_active_question_bank()
        if active_bank:
            df = load_questions_from_bank(active_bank['id'])
            if not df.empty:
                st.session_state.data = df
                st.session_state.current_file_name = active_bank['file_name']
                st.session_state.current_bank_name = active_bank['bank_name']
                st.session_state.current_bank_file = active_bank['file_name']
                st.session_state.current_bank_id = active_bank['id']
        else:
            banks = get_all_question_banks()
            if banks:
                df = load_questions_from_bank(banks[0]['id'])
                if not df.empty:
                    st.session_state.data = df
                    st.session_state.current_file_name = banks[0]['file_name']
                    st.session_state.current_bank_name = banks[0]['bank_name']
                    st.session_state.current_bank_file = banks[0]['file_name']
                    st.session_state.current_bank_id = banks[0]['id']
                    activate_question_bank(banks[0]['id'])

    if st.session_state.data is None:
        st.info("请先导入或选择题库")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📂 导入题库"):
                st.session_state.current_page = 'import'
                st.rerun()
        with col2:
            if st.button("📚 管理题库"):
                st.session_state.current_page = 'banks'
                st.rerun()
        return

    st.header("📚 开始刷题")

    df = st.session_state.data
    question_count = len(df)

    if st.session_state.current_bank_name:
        bank_name = st.session_state.current_bank_name
    else:
        active_bank = get_active_question_bank()
        if active_bank:
            bank_name = active_bank['bank_name']
            st.session_state.current_bank_name = bank_name
        else:
            bank_name = "未命名题库"

    display_bank_name = truncate_filename(bank_name, 30)
    st.info(f"当前题库: **{display_bank_name}** ({question_count}题)")

    if st.session_state.current_file_name and st.session_state.current_file_name != bank_name:
        display_file = truncate_filename(st.session_state.current_file_name, 40)
        st.caption(f"文件: {display_file}")

    # 错题重练模式返回按钮
    if (hasattr(st.session_state, 'practice_mode') and
            st.session_state.practice_mode == 'review' and
            st.session_state.original_bank_before_review and
            not st.session_state.quiz_active):
        col_back, col_info = st.columns([1, 3])
        with col_back:
            if st.button("🔙 返回原题库", type="secondary", use_container_width=True):
                original_bank = st.session_state.original_bank_before_review
                active_bank = get_active_question_bank()

                if not active_bank or original_bank['id'] != active_bank['id']:
                    if activate_question_bank(original_bank['id']):
                        df = load_questions_from_bank(original_bank['id'])
                        if not df.empty:
                            st.session_state.data = df
                            st.session_state.current_file_name = original_bank['file']
                            st.session_state.current_bank_name = original_bank['name']
                            st.session_state.current_bank_file = original_bank['file']
                            st.session_state.current_bank_id = original_bank['id']
                            st.session_state.review_mode = False
                            st.session_state.practice_mode = None
                            st.session_state.original_bank_before_review = None
                            st.success(f"已切换回原题库: {original_bank['name']}")
                            time.sleep(1)
                            st.rerun()
                else:
                    df = load_questions_from_bank(original_bank['id'])
                    if not df.empty:
                        st.session_state.data = df
                        st.session_state.current_file_name = original_bank['file']
                        st.session_state.current_bank_name = original_bank['name']
                        st.session_state.current_bank_file = original_bank['file']
                        st.session_state.current_bank_id = original_bank['id']
                        st.session_state.review_mode = False
                        st.session_state.practice_mode = None
                        st.session_state.original_bank_before_review = None
                        st.rerun()

        with col_info:
            st.caption(f"当前为错题本练习模式，原题库: {st.session_state.original_bank_before_review['name']}")

    elif st.session_state.review_mode and st.session_state.original_bank_before_review:
        col_back, col_info = st.columns([1, 3])
        with col_back:
            if st.button("🔙 返回原题库", type="secondary", use_container_width=True):
                original_bank = st.session_state.original_bank_before_review
                active_bank = get_active_question_bank()

                if original_bank['id'] != active_bank['id']:
                    if activate_question_bank(original_bank['id']):
                        df = load_questions_from_bank(original_bank['id'])
                        if not df.empty:
                            st.session_state.data = df
                            st.session_state.current_file_name = original_bank['file']
                            st.session_state.current_bank_name = original_bank['name']
                            st.session_state.current_bank_file = original_bank['file']
                            st.session_state.current_bank_id = original_bank['id']
                            st.session_state.review_mode = False
                            st.success(f"已切换回原题库: {original_bank['name']}")
                            time.sleep(1)
                            st.rerun()
                else:
                    df = load_questions_from_bank(original_bank['id'])
                    if not df.empty:
                        st.session_state.data = df
                        st.session_state.current_file_name = original_bank['file']
                        st.session_state.current_bank_name = original_bank['name']
                        st.session_state.current_bank_file = original_bank['file']
                        st.session_state.current_bank_id = original_bank['id']
                        st.session_state.review_mode = False
                        st.rerun()

        with col_info:
            st.caption(f"当前为错题本练习模式，原题库: {st.session_state.original_bank_before_review['name']}")

    st.subheader("1. 选择刷题模式")
    mode_col1, mode_col2, mode_col3 = st.columns(3)

    with mode_col1:
        if st.button("📖 顺序刷题", use_container_width=True, help="按顺序刷题"):
            st.session_state.practice_mode = 'sequential'
            st.rerun()

    with mode_col2:
        if st.button("🎲 随机刷题", use_container_width=True, help="随机抽取题目"):
            st.session_state.practice_mode = 'random'
            st.rerun()

    with mode_col3:
        wrong_list = get_wrong_questions()
        if st.button("📕 错题重练", use_container_width=True,
                     help="专门练习错题本中的题目", disabled=len(wrong_list) == 0):
            wrong_df = pd.DataFrame(wrong_list)
            st.session_state.data = wrong_df
            st.session_state.current_file_name = "错题本"
            st.session_state.current_bank_name = "错题本"
            st.session_state.practice_mode = 'review'
            st.session_state.wrong_book_random_mode = False

            if not st.session_state.original_bank_before_review:
                active_bank = get_active_question_bank()
                if active_bank:
                    st.session_state.original_bank_before_review = {
                        'id': active_bank['id'],
                        'name': active_bank['bank_name'],
                        'file': active_bank['file_name']
                    }

            st.rerun()

    if st.session_state.practice_mode:
        render_practice_settings()
    else:
        st.subheader("📊 当前题库信息")

        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("总题数", question_count)
        with col_info2:
            if '题型' in df.columns:
                st.metric("题型数量", df['题型'].nunique())
            else:
                st.metric("题型数量", "未知")
        with col_info3:
            file_name = st.session_state.current_file_name or "未命名"
            display_name = truncate_filename(file_name, 20)
            st.metric("文件", display_name)
            if len(file_name) > 20:
                st.caption(f"完整文件名: {file_name}")

        if '题型' in df.columns:
            st.subheader("题型分布")
            type_counts = df['题型'].value_counts()
            for q_type, count in type_counts.items():
                percentage = (count / question_count) * 100
                st.progress(count / question_count, text=f"{q_type}: {count}题 ({percentage:.1f}%)")


def render_practice_settings():
    """渲染刷题设置"""
    if not st.session_state.practice_mode:
        return

    df = st.session_state.data

    mode_titles = {
        'sequential': '📖 顺序刷题设置',
        'random': '🎲 随机刷题设置',
        'review': '📕 错题重练设置'
    }

    st.subheader(mode_titles.get(st.session_state.practice_mode, '刷题设置'))

    if st.session_state.practice_mode == 'review':
        wrong_files = get_wrong_book_files()

        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            if wrong_files:
                filter_options = ['全部'] + wrong_files
                current_filter = st.session_state.get('wrong_book_filter', '全部')
                selected_filter = st.selectbox(
                    "选择题库", filter_options,
                    index=filter_options.index(current_filter) if current_filter in filter_options else 0,
                    help="选择要重练错题的题库"
                )
                st.session_state.wrong_book_filter = selected_filter
            else:
                st.info("暂无错题记录")
                st.session_state.wrong_book_filter = '全部'
                st.selectbox("选择题库", ["全部"], index=0, disabled=True)

        with col_filter2:
            all_types = df['题型'].unique()
            default_types = list(all_types) if len(all_types) > 0 else []
            selected = st.multiselect("选择题型", all_types, default=default_types, help="选择要练习的题型")
            st.session_state.selected_types = selected

    else:
        col_set1, col_set2 = st.columns(2)
        with col_set1:
            all_types = df['题型'].unique()
            selected = st.multiselect("选择题型", all_types, default=list(all_types), help="选择要练习的题型")
            st.session_state.selected_types = selected

        with col_set2:
            st.session_state.time_limit = st.slider("每题限时(秒)", 10, 300, 30, help="每道题的回答时间限制")

    # 题目数量设置
    st.subheader("2. 题目数量设置")

    if st.session_state.practice_mode == 'review':
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
            filtered_wrong_list.append(wrong)

        wrong_count = len(filtered_wrong_list)
        max_questions = wrong_count

        if wrong_count > 0 and st.session_state.wrong_book_random_mode:
            if 'shared_count_review' not in st.session_state:
                st.session_state.shared_count_review = min(10, max_questions)

            def callback_slider_review():
                st.session_state.shared_count_review = st.session_state._slider_key_review
                st.session_state.question_count = st.session_state._slider_key_review
                st.session_state._input_key_review = st.session_state._slider_key_review

            def callback_input_review():
                st.session_state.shared_count_review = st.session_state._input_key_review
                st.session_state.question_count = st.session_state._input_key_review
                st.session_state._slider_key_review = st.session_state._input_key_review

            st.info(f"请输入或选择题目数量 (1-{max_questions})")

            col_slider, col_input = st.columns(2)
            with col_slider:
                st.slider("题目数量 (滑块)", min_value=1, max_value=max_questions,
                          key="_slider_key_review", on_change=callback_slider_review)
            with col_input:
                st.number_input("题目数量 (输入)", min_value=1, max_value=max_questions,
                                step=1, key="_input_key_review", on_change=callback_input_review)

            st.success(f"当前题目数量: {st.session_state.shared_count_review}")

        elif wrong_count > 0:
            st.session_state.question_count = wrong_count
            st.info(f"将顺序练习所有 {wrong_count} 道错题")

    else:
        filtered_df = df[df['题型'].isin(st.session_state.selected_types)] if st.session_state.selected_types else df
        max_questions = len(filtered_df)

        default_count = min(20, max_questions) if st.session_state.practice_mode == 'random' else max_questions

        if 'shared_count_regular' not in st.session_state:
            st.session_state.shared_count_regular = default_count

        def callback_slider_regular():
            st.session_state.shared_count_regular = st.session_state._slider_key_regular
            st.session_state.question_count = st.session_state._slider_key_regular
            st.session_state._input_key_regular = st.session_state._slider_key_regular

        def callback_input_regular():
            st.session_state.shared_count_regular = st.session_state._input_key_regular
            st.session_state.question_count = st.session_state._input_key_regular
            st.session_state._slider_key_regular = st.session_state._input_key_regular

        st.info(f"请输入或选择题目数量 (1-{max_questions})")

        col_slider, col_input = st.columns(2)
        with col_slider:
            st.slider("题目数量 (滑块)", min_value=1, max_value=max_questions,
                      key="_slider_key_regular", on_change=callback_slider_regular)
        with col_input:
            st.number_input("题目数量 (输入)", min_value=1, max_value=max_questions,
                            step=1, key="_input_key_regular", on_change=callback_input_regular)

        st.success(f"当前题目数量: {st.session_state.shared_count_regular}")

    with st.expander("⚙️ 高级选项"):
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            st.session_state.shuffle_mode = st.checkbox("随机打乱选项顺序", value=st.session_state.shuffle_mode)
        with col_adv2:
            if st.session_state.practice_mode != 'review':
                st.session_state.auto_timeout = st.checkbox("超时自动提交", value=True)

    with st.expander("⌨️ 键盘控制设置"):
        col_key1, col_key2 = st.columns(2)
        with col_key1:
            st.session_state.keyboard_control = st.checkbox(
                "启用键盘控制", value=st.session_state.keyboard_control,
                help="启用键盘控制答题（数字键选择选项，Enter提交）"
            )
        with col_key2:
            if st.session_state.keyboard_control:
                st.info("📝 使用说明：\n• 数字键1-6选择对应选项\n• Enter键提交答案\n• ← → 键切换题目")
            else:
                st.info("禁用键盘控制")

    st.divider()
    col_start, col_back = st.columns([2, 1])

    with col_start:
        disabled = False
        if st.session_state.practice_mode == 'review':
            wrong_list = get_wrong_questions()
            filtered_count = 0
            for wrong in wrong_list:
                q_type = wrong.get('题型', '')
                if st.session_state.selected_types and q_type not in st.session_state.selected_types:
                    continue
                if (hasattr(st.session_state, 'wrong_book_filter') and
                        st.session_state.wrong_book_filter and
                        st.session_state.wrong_book_filter != '全部'):
                    file_name = wrong.get('_file_name', '')
                    if file_name != st.session_state.wrong_book_filter:
                        continue
                filtered_count += 1
            if filtered_count == 0:
                disabled = True
                st.warning("没有符合条件的错题")

        if st.button("🚀 开始刷题", type="primary", use_container_width=True, disabled=disabled):
            if not st.session_state.selected_types:
                st.error("请至少选择一种题型")
            else:
                start_quiz(st.session_state.practice_mode)
                st.rerun()

    with col_back:
        if st.button("返回", type="secondary", use_container_width=True):
            st.session_state.practice_mode = None
            st.rerun()
