"""题库管理页面"""
import streamlit as st
import time

from database import (
    get_all_question_banks, activate_question_bank, load_questions_from_bank,
    delete_question_bank
)
from utils import truncate_filename


def render_bank_management():
    """渲染题库管理页面"""
    st.header("📚 题库管理")

    banks = get_all_question_banks()

    col_add, col_stats = st.columns([1, 3])
    with col_add:
        if st.button("📥 导入新题库", type="primary", use_container_width=True):
            st.session_state.current_page = 'import'
            st.rerun()

    with col_stats:
        if banks:
            active_banks = [b for b in banks if b['is_active'] == 1]
            if active_banks:
                active_bank = active_banks[0]
                display_name = truncate_filename(active_bank['bank_name'], 30)
                st.info(f"当前使用: {display_name} ({active_bank['total_questions']}题)")

    if banks:
        st.subheader("📋 题库列表")

        for bank in banks:
            with st.container():
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])

                with col1:
                    if bank['is_active']:
                        st.markdown(f"**✅ {bank['bank_name']}**")
                    else:
                        st.markdown(f"**📂 {bank['bank_name']}**")

                    display_file = truncate_filename(bank['file_name'], 25)
                    st.caption(f"文件: {display_file} | {bank['total_questions']}题")

                    if bank['question_types']:
                        type_str = ", ".join([f"{k}:{v}" for k, v in bank['question_types'].items()])
                        st.caption(f"题型: {type_str}")

                with col2:
                    if bank['import_time']:
                        import_date = bank['import_time'].split()[0] if isinstance(bank['import_time'], str) else bank['import_time']
                        st.caption(f"导入: {import_date}")

                with col3:
                    if not bank['is_active']:
                        if st.button("使用", key=f"use_{bank['id']}", use_container_width=True):
                            if activate_question_bank(bank['id']):
                                df = load_questions_from_bank(bank['id'])
                                if not df.empty:
                                    st.session_state.data = df
                                    st.session_state.current_file_name = bank['file_name']
                                    st.session_state.current_bank_name = bank['bank_name']
                                    st.session_state.current_bank_file = bank['file_name']
                                    st.session_state.current_bank_id = bank['id']
                                    st.success(f"已切换到题库: {bank['bank_name']}")
                                    time.sleep(1)
                                    st.rerun()

                with col4:
                    if st.button("删除", key=f"del_{bank['id']}", type="secondary", use_container_width=True):
                        if delete_question_bank(bank['id']):
                            st.success(f"已删除题库: {bank['bank_name']}")
                            time.sleep(1)
                            st.rerun()

                st.divider()
    else:
        st.info("暂无题库，请先导入题库")
        st.markdown("""
        ### 💡 题库管理功能说明

        1. **导入题库**：点击上方"导入新题库"按钮，导入您的题库文件
        2. **保存题库**：导入时会自动保存到题库库，避免重复导入
        3. **切换题库**：在题库列表中点击"使用"按钮切换不同题库
        4. **删除题库**：可以删除不再需要的题库
        5. **当前题库**：标有✅的为当前正在使用的题库

        题库管理功能让您可以轻松管理多个题库，无需重复导入相同文件。
        """)
