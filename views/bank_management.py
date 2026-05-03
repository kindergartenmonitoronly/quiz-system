"""题库管理页面"""
import streamlit as st
import time

from database import (
    get_all_question_banks, activate_question_bank, load_questions_from_bank,
    delete_question_bank
)
from utils import truncate_filename

TYPE_COLORS = {
    '单选题': '#2196F3', '多选题': '#9C27B0', '判断题': '#FF9800', '填空题': '#009688'
}


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
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:10px;
                padding:12px 16px;border-left:4px solid #4CAF50">
                    <span style="color:#2e7d32;font-weight:bold">✅ 当前题库</span><br>
                    <span style="font-size:16px">{active_bank['bank_name']}</span>
                    <span style="color:#666;margin-left:8px">{active_bank['total_questions']}题</span>
                </div>
                """, unsafe_allow_html=True)

    if not banks:
        st.info("暂无题库，请先导入题库")
        st.markdown("""
        ### 💡 题库管理功能说明
        1. **导入题库**：点击上方"导入新题库"按钮
        2. **自动去重**：相同题库不会重复导入
        3. **一键切换**：在题库卡片中点击"使用"切换
        4. **安全删除**：当前使用的题库不会被误删
        """)
        return

    st.subheader(f"📋 题库列表 ({len(banks)}个)")

    for bank in banks:
        is_active = bank['is_active'] == 1
        border_color = '#4CAF50' if is_active else '#e0e0e0'
        bg_color = '#f1f8e9' if is_active else '#fafafa'
        badge_text = '✅ 使用中' if is_active else '📂 待用'

        # 构建题型标签
        type_tags = ''
        if bank['question_types']:
            for qtype, count in bank['question_types'].items():
                color = TYPE_COLORS.get(qtype, '#757575')
                type_tags += f'<span style="display:inline-block;background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;margin:2px">{qtype} {count}</span> '

        # 导入日期
        import_date = ''
        if bank['import_time']:
            raw = bank['import_time']
            import_date = raw.split()[0] if isinstance(raw, str) else str(raw)[:10]

        st.markdown(f"""
        <div style="background:{bg_color};border:1px solid {border_color};border-radius:12px;
        padding:16px;margin:8px 0;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <span style="font-size:16px;font-weight:bold">{bank['bank_name']}</span>
                    <span style="background:{'#4CAF50' if is_active else '#9e9e9e'};color:white;
                    padding:2px 10px;border-radius:10px;font-size:11px;margin-left:8px">{badge_text}</span>
                </div>
                <div style="color:#888;font-size:12px">{import_date}</div>
            </div>
            <div style="margin:8px 0;color:#666;font-size:13px">
                文件: {truncate_filename(bank['file_name'], 30)} &nbsp;|&nbsp; 共 <b>{bank['total_questions']}</b> 题
            </div>
            <div style="margin:6px 0">{type_tags}</div>
        </div>
        """, unsafe_allow_html=True)

        col_use, col_del, col_spacer = st.columns([1, 1, 4])
        with col_use:
            if not is_active:
                if st.button("✅ 使用", key=f"use_{bank['id']}", use_container_width=True):
                    if activate_question_bank(bank['id']):
                        df = load_questions_from_bank(bank['id'])
                        if not df.empty:
                            st.session_state.data = df
                            st.session_state.current_file_name = bank['file_name']
                            st.session_state.current_bank_name = bank['bank_name']
                            st.session_state.current_bank_file = bank['file_name']
                            st.session_state.current_bank_id = bank['id']
                            # 重置计数状态
                            for k in ['shared_count_regular', '_slider_key_regular', '_input_key_regular',
                                       'shared_count_review', '_slider_key_review', '_input_key_review',
                                       'question_count', 'selected_types', 'practice_mode']:
                                if k in st.session_state:
                                    del st.session_state[k]
                            st.success(f"已切换到: {bank['bank_name']}")
                            time.sleep(0.5)
                            st.rerun()
            else:
                st.button("✅ 使用", key=f"use_{bank['id']}", disabled=True, use_container_width=True)

        with col_del:
            if st.button("🗑️ 删除", key=f"del_{bank['id']}", use_container_width=True):
                if delete_question_bank(bank['id']):
                    st.toast(f"已删除: {bank['bank_name']}")
                    time.sleep(0.5)
                    st.rerun()
