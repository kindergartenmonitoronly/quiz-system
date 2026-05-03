"""仪表盘页面"""
import streamlit as st
import base64

from database import get_all_question_banks, get_study_history, get_wrong_questions
from utils import create_template_download, truncate_filename


def render_dashboard():
    """渲染仪表盘"""
    st.header("🏠 智能刷题系统 Pro v3.5")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("""
        ### 🚀 主要功能

        **1. 📚 题库管理**
        - 导入Excel/CSV题库文件
        - 智能列名自动匹配
        - 题库库管理，避免重复导入
        - 多题库切换和管理

        **2. 📖 刷题模式**
        - 顺序刷题：按顺序练习所有题目
        - 随机刷题：随机抽取题目练习
        - 错题重练：专门练习答错的题目

        **3. 🎯 学习辅助**
        - 计时功能：每题限时，提高效率
        - 学习统计：记录学习进度和正确率
        - 智能错题本：记录错误次数，按错误次数排序
        - 学习进度管理：保存和继续上次刷题进度
        - 答题卡功能：查看答题情况，快速跳转

        **4. ⚡ 特色功能**
        - 选项随机打乱：防止记忆答案
        - 数据导出：导出错题本和学习报告
        - 学习分析：可视化学习进度
        - 智能题型识别：自动识别单选题、多选题、判断题、填空题
        - 鼠标滚轮调整：方便调整题目数量
        - 键盘控制：支持键盘快速答题
        - 错题本筛选清空：按条件清空错题
        """)

    with col2:
        st.markdown("### 📊 系统状态")

        if st.session_state.current_bank_name:
            bank_name = st.session_state.current_bank_name
            display_name = truncate_filename(bank_name, 15)
            st.metric("当前题库", display_name)
            if st.session_state.data is not None:
                st.caption(f"{len(st.session_state.data)}题")
        elif st.session_state.data is not None:
            df = st.session_state.data
            st.metric("题库题数", len(df))
            if '题型' in df.columns:
                st.metric("题型种类", df['题型'].nunique())
        else:
            st.info("尚未加载题库")

        banks = get_all_question_banks()
        if banks:
            st.metric("题库数量", len(banks))

    with col3:
        st.markdown("### 📈 学习记录")

        try:
            history_df = get_study_history(1)
            if not history_df.empty:
                today_stats = history_df.iloc[0]
                st.metric("今日刷题", today_stats['total_questions'])
                st.metric("今日正确率", f"{today_stats['accuracy']:.1f}%")
            else:
                st.info("今日尚未学习")
                st.metric("今日刷题", 0)
                st.metric("今日正确率", "0.0%")
        except Exception:
            st.metric("今日刷题", 0)
            st.metric("今日正确率", "0.0%")
            st.caption("数据加载中...")

        try:
            wrong_list = get_wrong_questions(limit=10)
            if wrong_list:
                total_errors = sum(q.get('_error_count', 1) for q in wrong_list)
                st.metric("错题数量", f"{len(wrong_list)}道")
                if len(wrong_list) > 0:
                    avg_errors = total_errors / len(wrong_list)
                    st.caption(f"平均错误次数: {avg_errors:.1f}次/题")
        except Exception:
            st.metric("错题数量", "0道")
            st.caption("数据加载中...")

    st.divider()
    st.subheader("⚡ 快速开始")

    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)

    with quick_col1:
        if st.button("📂 导入题库", use_container_width=True, help="导入新的题库文件"):
            st.session_state.current_page = 'import'
            st.rerun()

    with quick_col2:
        if st.session_state.data is not None:
            if st.button("📚 开始刷题", use_container_width=True, help="选择模式开始刷题"):
                st.session_state.current_page = 'practice'
                st.rerun()
        else:
            st.button("📚 开始刷题", use_container_width=True, disabled=True, help="请先导入题库")

    with quick_col3:
        if st.button("📚 题库管理", use_container_width=True, help="管理已导入的题库"):
            st.session_state.current_page = 'banks'
            st.rerun()

    with quick_col4:
        if st.button("📕 查看错题本", use_container_width=True, help="查看和管理错题"):
            st.session_state.current_page = 'wrong_book'
            st.rerun()

    st.divider()
    st.subheader("📋 下载标准模板")

    st.markdown("""
    **💡 提示：** 如果您有PDF题库，可以使用AI工具（如ChatGPT、文心一言等）将PDF内容转换为标准格式。
    """)

    template_df = create_template_download()

    st.markdown("**综合题库模板（包含题号和题型列，4种题型示例）**")

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <a href="data:file/csv;base64,{base64.b64encode(template_df.to_csv(index=False, encoding='utf-8-sig').encode()).decode()}" download="综合题库模板.csv"
           style="
                color: white;
                text-decoration: none;
                font-size: 16px;
                font-weight: bold;
                display: block;
                padding: 8px;
           ">
            📥 下载综合题库模板（包含题号和题型列，4种题型示例）
        </a>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📄 查看模板内容"):
        st.markdown("**模板包含以下示例题目：**")
        preview_df = template_df.copy()
        preview_cols = ['题号', '题型', '题目', '答案']
        if '解析' in preview_df.columns:
            preview_cols.append('解析')
        st.dataframe(preview_df[preview_cols], use_container_width=True)
        st.caption("模板包含题号、题型列，以及单选题、多选题、判断题、填空题各1道示例题")

    st.divider()
    st.subheader("📖 使用指南")

    guide_col1, guide_col2, guide_col3 = st.columns(3)

    with guide_col1:
        st.markdown("""
        **第一步：准备题库**
        1. 下载标准模板
        2. 整理题库到模板格式
        3. 保存为Excel或CSV文件

        **💡 AI转换提示：**
        ```
        请将以下PDF内容转换为题库：
        - 题号：[题目编号]
        - 题型：[题型：单选题/多选题/判断题/填空题]
        - 题目：[题目内容]
        - 答案：[正确答案]
        - 选项：[选项列表]
        - 解析：[答案解析]
        ```
        """)

    with guide_col2:
        st.markdown("""
        **第二步：导入题库**
        1. 点击"导入题库"
        2. 上传准备好的文件
        3. 配置列名映射
        4. 确认导入并保存到题库库

        **💡 导入技巧：**
        - 系统会自动匹配列名
        - 可手动调整映射关系
        - 支持多种文件编码
        - 题库会自动保存，避免重复导入
        """)

    with guide_col3:
        st.markdown("""
        **第三步：学习提升**
        1. 选择刷题模式
        2. 设置练习参数
        3. 开始答题练习
        4. 查看错题统计
        5. 使用答题卡复盘

        **💡 学习建议：**
        - 每天坚持练习20-30题
        - 重点关注错题本中的高频错题
        - 定期查看学习统计
        - 利用题库管理切换不同练习内容
        - 使用学习进度管理继续未完成的练习
        - 启用键盘控制提高答题效率
        """)
