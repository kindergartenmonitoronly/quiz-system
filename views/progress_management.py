"""学习进度管理页面"""
import streamlit as st
import time
import json

from database import (
    get_all_study_progress, load_questions_from_bank, delete_study_progress
)
from quiz_engine import start_quiz


def render_progress_management():
    """渲染学习进度管理页面"""
    st.header("📋 学习进度管理")

    progress_list = get_all_study_progress()

    if progress_list:
        st.info(f"您有 {len(progress_list)} 个未完成的刷题进度")

        for progress in progress_list:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**{progress['bank_name']}**")
                    mode_text = (
                        "顺序刷题" if progress['practice_mode'] == 'sequential'
                        else "随机刷题" if progress['practice_mode'] == 'random'
                        else "错题重练"
                    )
                    st.caption(f"{mode_text} | 进度: {progress['current_index'] + 1}/{progress['total_questions']}题")

                with col2:
                    if progress['start_time']:
                        start_date = progress['start_time'].split()[0] if isinstance(progress['start_time'], str) else progress['start_time']
                        st.caption(f"开始: {start_date}")

                with col3:
                    if progress['last_update']:
                        last_update = progress['last_update'].split()[0] if isinstance(progress['last_update'], str) else progress['last_update']
                        st.caption(f"最后更新: {last_update}")

                with col4:
                    col_cont, col_del = st.columns(2)
                    with col_cont:
                        if st.button("继续", key=f"cont_{progress['id']}", use_container_width=True):
                            df = load_questions_from_bank(progress['bank_id'])
                            if not df.empty:
                                st.session_state.data = df
                                st.session_state.current_file_name = progress['file_name']
                                st.session_state.current_bank_name = progress['bank_name']
                                st.session_state.current_bank_file = progress['file_name']
                                st.session_state.current_bank_id = progress['bank_id']
                                st.session_state.practice_mode = progress['practice_mode']
                                st.session_state.continue_progress = True
                                st.session_state.current_progress_id = progress['id']

                                if 'question_results' in progress:
                                    if isinstance(progress['question_results'], str):
                                        try:
                                            progress['question_results'] = json.loads(progress['question_results'])
                                        except Exception:
                                            progress['question_results'] = []
                                else:
                                    progress['question_results'] = []

                                if 'total_questions' not in progress:
                                    progress['total_questions'] = len(df)

                                start_quiz(progress['practice_mode'], True, progress)
                                st.rerun()
                    with col_del:
                        if st.button("删除", key=f"del_prog_{progress['id']}", type="secondary", use_container_width=True):
                            if delete_study_progress(progress['id']):
                                st.success("已删除进度")
                                time.sleep(0.5)
                                st.rerun()

                st.divider()
    else:
        st.info("暂无学习进度记录")
        st.markdown("""
        ### 💡 学习进度功能说明

        1. **自动保存**：刷题过程中会自动保存进度
        2. **继续学习**：可以继续上次未完成的刷题
        3. **多进度管理**：支持多个题库的刷题进度
        4. **进度清理**：可以删除不再需要的进度记录

        系统会在以下情况自动保存进度：
        - 每答完一题自动保存
        - 退出刷题时自动保存
        - 刷新页面时自动保存
        """)

    col_back, col_clear = st.columns(2)
    with col_back:
        if st.button("返回", type="secondary", use_container_width=True):
            st.session_state.current_page = 'practice'
            st.rerun()
    with col_clear:
        if st.button("清理所有已完成进度", type="secondary", use_container_width=True):
            st.info("该功能正在开发中")
