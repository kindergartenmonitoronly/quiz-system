"""导入题库页面（三步流程）"""
import re
import time
import streamlit as st
import pandas as pd

from ui_components import render_preview_table
from utils import (
    auto_match_columns, check_mapping_duplicates, clean_question_data,
    validate_data, create_template_download, download_template, truncate_filename
)


def render_import_page():
    """渲染导入题库页面"""
    st.header("📂 导入题库")

    steps = {'upload': ('📤 上传文件', 1), 'mapping': ('🔧 配置映射', 2), 'confirm': ('✅ 确认导入', 3)}
    current_step_name, current_step_num = steps.get(st.session_state.import_step, ('上传文件', 1))

    # 步骤进度条
    st.progress(current_step_num / 3, text=f"步骤 {current_step_num}/3: {current_step_name}")
    cols = st.columns(3)
    for i, (label, num) in enumerate([
        ('📤 上传', 1), ('🔧 映射', 2), ('✅ 确认', 3)
    ]):
        with cols[i]:
            if num < current_step_num:
                st.success(label)
            elif num == current_step_num:
                st.info(f"**{label}** ←")
            else:
                st.caption(label)

    st.divider()

    if st.session_state.import_step == 'upload':
        render_upload_step()
    elif st.session_state.import_step == 'mapping':
        render_mapping_step()
    elif st.session_state.import_step == 'confirm':
        render_confirm_step()


def render_upload_step():
    """渲染上传步骤"""
    st.markdown("""
    ### 步骤 1: 上传文件
    - 支持 Excel (.xlsx, .xls) 和 CSV 格式
    - 文件应包含题目、答案等必要信息
    - 建议文件大小不超过 10MB
    - 下载下方模板了解标准格式
    """)

    template_df = create_template_download()

    with st.expander("📋 下载标准模板", expanded=False):
        st.markdown("**综合题库模板（包含题号和题型列）**")
        st.markdown(download_template(template_df, "综合题库模板"), unsafe_allow_html=True)

        st.markdown("**模板预览:**")
        preview_df = template_df.copy()
        preview_cols = ['题号', '题型', '题目', '答案']
        if '解析' in preview_df.columns:
            preview_cols.append('解析')
        st.dataframe(preview_df[preview_cols].head(3), use_container_width=True)
        st.caption("模板包含题号、题型列，以及单选题、多选题、判断题、填空题各1道示例题")

    uploaded_file = st.file_uploader("选择文件", type=['xlsx', 'xls', 'csv'],
                                     help="请上传题库文件", key="file_uploader")

    if uploaded_file:
        try:
            if uploaded_file.name != st.session_state.current_file_name:
                st.session_state.current_file_name = uploaded_file.name
                st.session_state.current_bank_name = None
                st.session_state.current_bank_file = None
                st.session_state.option_columns_count = 4
                st.session_state.file_uploaded = True
                file_size = uploaded_file.size / 1024

                if file_size > 10240:
                    st.warning(f"文件较大 ({file_size / 1024:.1f}MB)，处理可能需要时间")

                with st.spinner("读取文件中..."):
                    if uploaded_file.name.endswith('.csv'):
                        try:
                            df = pd.read_csv(uploaded_file, encoding='utf-8')
                        except UnicodeDecodeError:
                            try:
                                df = pd.read_csv(uploaded_file, encoding='gbk')
                            except UnicodeDecodeError:
                                df = pd.read_csv(uploaded_file, encoding='latin1')
                    else:
                        df = pd.read_excel(uploaded_file)

                if df is not None and not df.empty:
                    st.session_state.original_data = df
                    st.session_state.column_mapping = auto_match_columns(df.columns.tolist())

                    st.success(f"✅ 成功读取文件: {uploaded_file.name}")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("总行数", len(df))
                    col2.metric("总列数", len(df.columns))
                    col3.metric("文件大小", f"{file_size:.1f}KB")

                    st.subheader("📊 数据预览（前5行，截断显示）")
                    render_preview_table(df, truncate_chars=3, show_all=True)
                else:
                    st.error("读取的文件为空")
                    return
            else:
                df = st.session_state.original_data
                if df is not None:
                    st.info(f"已加载文件: {uploaded_file.name}")

            if st.button("下一步：配置列映射", type="primary", key="next_to_mapping"):
                if st.session_state.original_data is not None:
                    st.session_state.import_step = 'mapping'
                    st.rerun()
                else:
                    st.error("请先上传文件")

        except Exception as e:
            st.error(f"读取失败: {str(e)}")
    else:
        # AI 转换提示 + 一键复制跳转豆包
        ai_prompt = """请将以下内容转换为标准题库格式（CSV），要求：
- 列顺序：题号,题型,题目,答案,选项A,选项B,选项C,选项D,选项E,选项F,解析
- 题型必须是：单选题、多选题、判断题、填空题 之一
- 数学/化学公式使用 LaTeX 语法，包裹在 $...$（行内）或 $$...$$（块级）中
- 判断题答案用 A（正确）或 B（错误）
- 多选题答案用连续字母如 ABC
- 直接输出 CSV 内容，不要额外解释"""
        col_prompt, col_btn = st.columns([3, 1])
        with col_prompt:
            with st.expander("🤖 AI 转换提示词（点击展开）", expanded=False):
                st.code(ai_prompt, language="markdown")
        with col_btn:
            import base64 as _b64
            prompt_b64 = _b64.b64encode(ai_prompt.encode()).decode()
            components.html(f"""
            <div style="display:flex;flex-direction:column;gap:8px;align-items:center;padding-top:8px">
            <button onclick="
                navigator.clipboard.writeText(atob('{prompt_b64}'));
                window.open('https://www.doubao.com/chat/', '_blank');
            " style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;
            padding:10px 20px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:bold;width:100%">
            📋 复制并打开豆包
            </button>
            <span style="font-size:11px;color:var(--text-muted)">点击复制提示词并跳转</span>
            </div>
            """, height=90)

        st.info("### 📄 数据格式示例")
        st.markdown("""
        **标准格式CSV文件结构：**
        ```
        题号,题型,题目,答案,选项A,选项B,选项C,选项D,选项E,选项F,解析
        1,单选题,Python是一种什么样的语言？,A,一种高级编程语言,一种数据库系统,一种操作系统,一种硬件设备,,,解析内容
        2,多选题,下列哪些是Python的特点？,ABC,简单易学,开源免费,跨平台,编译型语言,,,解析内容
        ```
        """)
        st.markdown("**对应的数据表格示例：**")
        example_data = pd.DataFrame({
            '题号': [1, 2],
            '题型': ['单选题', '多选题'],
            '题目': ['示例题目1：Python是什么语言？', '示例题目2：Python的特点包括？'],
            '答案': ['A', 'AB'],
            '选项A': ['高级编程语言', '简单易学'],
            '选项B': ['数据库系统', '开源免费'],
            '选项C': ['操作系统', '跨平台'],
            '选项D': ['硬件设备', '编译型语言'],
            '选项E': ['', ''],
            '选项F': ['', ''],
            '解析': ['Python是一种高级编程语言', 'Python是解释型语言，不是编译型']
        })
        st.dataframe(example_data.fillna(''), use_container_width=True)
        st.caption("💡 提示：模板包含题号、题型列，6个选项列（A-F），填空题和判断题等题型可以只填写必要的选项列")


def render_mapping_step():
    """渲染映射配置步骤"""
    if st.session_state.original_data is None:
        st.error("请先上传文件")
        st.session_state.import_step = 'upload'
        st.rerun()
        return

    df_raw = st.session_state.original_data
    cols = df_raw.columns.tolist()

    st.markdown("### 步骤 2: 配置列映射")
    st.markdown("请将系统列名映射到您的数据列名")

    with st.expander("📊 原始数据预览（前5行，截断显示）", expanded=True):
        render_preview_table(df_raw, truncate_chars=3, show_all=True)

    st.subheader("🔧 映射配置")

    if not st.session_state.column_mapping:
        st.session_state.column_mapping = auto_match_columns(cols)

    mapping = st.session_state.column_mapping

    # 分析答案列 + 文件列名，动态确定所需选项数量
    max_option_needed = 0
    answer_column = mapping.get('答案', '')
    if answer_column and answer_column in df_raw.columns:
        for answer in df_raw[answer_column].dropna().astype(str):
            letters = re.findall(r'[A-F]', answer.upper())
            if letters:
                max_letter = max(letters)
                option_index = ord(max_letter) - ord('A') + 1
                if option_index > max_option_needed:
                    max_option_needed = option_index
    # 同时扫描文件列名中的选项列（选项A-选项F）
    col_option_count = sum(1 for c in cols if re.match(r'选项[A-F]', c))
    max_option_needed = max(max_option_needed, col_option_count)

    required_options = max(2, min(6, max_option_needed))
    # 只在首次加载时自动设置，之后由用户手动调整
    if not st.session_state.get('_option_count_set', False):
        st.session_state.option_columns_count = required_options
        st.session_state._option_count_set = True

    # 基本字段映射
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        current_number = mapping.get('题号', '[不映射]')
        number_options = ['[不映射]'] + cols
        number_index = 0
        if current_number in cols:
            number_index = cols.index(current_number) + 1
        mapping['题号'] = st.selectbox("题号列", number_options, index=number_index, help="选择题号列（可选）")

    with col2:
        current_type = mapping.get('题型', '[不映射]')
        type_options = ['[不映射]'] + cols
        type_index = 0
        if current_type in cols:
            type_index = cols.index(current_type) + 1
        mapping['题型'] = st.selectbox("题型列", type_options, index=type_index, help="选择题型列（可选，系统会自动识别）")

    with col3:
        current_title = mapping.get('题目', '')
        title_index = 0
        if current_title in cols:
            title_index = cols.index(current_title)
        mapping['题目'] = st.selectbox("题目列 *", cols, index=title_index, help="选择包含题目内容的列")

    with col4:
        current_answer = mapping.get('答案', '')
        answer_index = 0
        if current_answer in cols:
            answer_index = cols.index(current_answer)
        mapping['答案'] = st.selectbox("答案列 *", cols, index=answer_index, help="选择包含答案的列")

    with col5:
        current_explanation = mapping.get('解析', '[不映射]')
        explanation_options = ['[不映射]'] + cols
        explanation_index = 0
        if current_explanation in cols:
            explanation_index = cols.index(current_explanation) + 1
        mapping['解析'] = st.selectbox("解析列", explanation_options, index=explanation_index, help="选择包含解析的列（可选）")

    # 高级选项
    with st.expander("⚙️ 高级选项", expanded=True):
        opt_n = st.session_state.option_columns_count
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;
        background:var(--bg-card);padding:12px 16px;border-radius:10px;
        border:1px solid var(--border-default)">
            <span style="font-weight:bold;font-size:15px">📊 选项列数量</span>
            <span style="font-size:28px;font-weight:bold;color:#4CAF50;min-width:36px;text-align:center">{opt_n}</span>
            <span style="color:var(--text-muted);font-size:13px">列 (2~6)</span>
            <div style="flex:1"></div>
        </div>
        """, unsafe_allow_html=True)
        col_minus, col_plus, col_info = st.columns([1, 1, 4])
        with col_minus:
            if st.button("➖ 减少", key="decrease_option_count", use_container_width=True,
                         disabled=opt_n <= 2):
                st.session_state.option_columns_count = max(2, opt_n - 1)
                st.rerun()
        with col_plus:
            if st.button("➕ 增加", key="increase_option_count", use_container_width=True,
                         disabled=opt_n >= 6):
                st.session_state.option_columns_count = min(6, opt_n + 1)
                st.rerun()
        with col_info:
            letters = [f'选项{chr(65 + i)}' for i in range(opt_n)]
            st.caption(f"当前映射: {', '.join(letters)}")
            if max_option_needed > opt_n:
                st.warning(f"⚠️ 答案中检测到选项 {chr(65 + max_option_needed - 1)}，建议至少 {max_option_needed} 列")

        st.markdown("**🔠 选项列映射**")
        opt_count = st.session_state.option_columns_count

        for row_start in range(0, opt_count, 3):
            row_cols = st.columns(3)
            for col_idx in range(3):
                i = row_start + col_idx
                if i < opt_count:
                    letter = chr(65 + i)
                    option_key = f'选项{letter}'
                    current_option = mapping.get(option_key, '[不映射]')
                    option_options = ['[不映射]'] + cols
                    option_index = 0
                    if current_option in cols:
                        option_index = cols.index(current_option) + 1
                    with row_cols[col_idx]:
                        mapping[option_key] = st.selectbox(f"选项{letter}列", option_options,
                                                           index=option_index, key=f"opt_map_{letter}")

    st.session_state.column_mapping = mapping
    mapping_errors = check_mapping_duplicates(mapping)

    if mapping_errors:
        st.error("映射配置错误:")
        for error in mapping_errors:
            st.write(error)

    col_back, col_test, col_next = st.columns([1, 1, 2])

    with col_back:
        if st.button("上一步", use_container_width=True):
            st.session_state.import_step = 'upload'
            st.session_state.show_test_mapping_result = False
            st.rerun()

    with col_test:
        if st.button("测试映射", type="secondary", use_container_width=True):
            clean_map = {k: v for k, v in mapping.items() if v != '[不映射]'}
            try:
                test_df = clean_question_data(df_raw.head(10), clean_map)
                if not test_df.empty:
                    st.session_state.test_mapping_df = test_df
                    st.session_state.show_test_mapping_result = True
                    st.success(f"✅ 映射测试成功，生成 {len(test_df)} 行数据")
                else:
                    st.warning("⚠️ 映射测试成功，但未生成有效数据")
                    st.session_state.show_test_mapping_result = False
            except Exception as e:
                st.error(f"❌ 映射测试失败: {str(e)}")
                st.session_state.show_test_mapping_result = False

    with col_next:
        disabled = bool(mapping_errors)
        if st.button("确认并清洗数据", type="primary", use_container_width=True, disabled=disabled):
            clean_map = {k: v for k, v in mapping.items() if v != '[不映射]'}
            cleaned_df = clean_question_data(df_raw, clean_map)

            if not cleaned_df.empty:
                st.session_state.data = cleaned_df
                st.session_state.data_cleaned = True

                warnings = validate_data(cleaned_df)
                if warnings:
                    st.warning("数据质量检查:")
                    for warning in warnings:
                        st.write(f"- {warning}")

                st.session_state.import_step = 'confirm'
                st.rerun()
            else:
                st.error("数据清洗后为空，请检查映射设置")

    if st.session_state.get('show_test_mapping_result', False) and st.session_state.test_mapping_df is not None:
        st.divider()
        with st.expander("📊 查看测试结果详情", expanded=True):
            display_test_df = st.session_state.test_mapping_df.copy()
            display_test_df = display_test_df.fillna('')
            for col in display_test_df.columns:
                display_test_df[col] = display_test_df[col].astype(str).apply(
                    lambda x: x[:50] + '...' if len(x) > 50 else x
                )
            st.dataframe(display_test_df, use_container_width=True)
            st.caption(f"测试结果预览（共{len(display_test_df)}行，每单元格最多显示50个字符）")

            if '题型' in display_test_df.columns:
                st.subheader("📈 测试题型分布")
                type_counts = display_test_df['题型'].value_counts()
                if len(type_counts) > 0:
                    type_cols = st.columns(len(type_counts))
                    for idx, (q_type, count) in enumerate(type_counts.items()):
                        with type_cols[idx]:
                            percentage = (count / len(display_test_df)) * 100
                            st.metric(q_type, count, f"{percentage:.1f}%")

                with st.expander("🔍 题型识别详情", expanded=False):
                    for idx, row in display_test_df.iterrows():
                        st.write(f"**第{idx + 1}题:** {row['题目'][:80]}...")
                        st.write(f"- 题型: {row.get('题型', '未知')}")
                        st.write(f"- 答案: {row.get('答案', '未知')}")
                        if '解析' in row and row['解析']:
                            st.write(f"- 解析: {row['解析'][:100]}...")
                        st.divider()


def render_confirm_step():
    """渲染确认步骤"""
    if st.session_state.data is None:
        st.error("数据未加载")
        st.session_state.import_step = 'upload'
        st.rerun()
        return

    df = st.session_state.data

    st.success("✅ 数据导入成功！")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总题数", len(df))
    col2.metric("题型数量", df['题型'].nunique())
    col3.metric("有解析题目", df['解析'].str.strip().ne('').sum())

    total_questions = len(df)

    with st.expander("📊 数据预览（每种题型各预览1题）", expanded=True):
        render_preview_table(df, truncate_chars=50, show_all=False)

    st.subheader("📈 题型分析")

    if st.session_state.type_analysis:
        analysis = st.session_state.type_analysis
        issues = analysis.get('potential_issues', [])

        if issues:
            st.warning(f"⚠️ 发现 {len(issues)} 道可疑题目（题型可能识别错误）")

            # 从完整数据中提取可疑题目行号
            issue_indices = []
            for issue in issues:
                match = re.search(r'第(\d+)行', issue)
                if match:
                    issue_indices.append(int(match.group(1)) - 1)

            st.subheader("✏️ 修正可疑题目")
            view_mode = st.radio("显示范围", ["仅可疑题目", "全部题目"], horizontal=True, key="edit_view_mode")

            if view_mode == "仅可疑题目" and issue_indices:
                edit_df = df.iloc[issue_indices].copy()
                st.caption(f"显示 {len(issue_indices)} 道可疑题目（共 {len(df)} 题）")

                for i, issue in enumerate(issues[:5]):
                    st.caption(f"• {issue.split(chr(10))[0]}")
                if len(issues) > 5:
                    st.caption(f"… 还有 {len(issues) - 5} 个问题")
            else:
                edit_df = df

            edited_df = st.data_editor(
                edit_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    '题号': st.column_config.NumberColumn('题号', width='small'),
                    '题型': st.column_config.SelectboxColumn('题型', options=['单选题', '多选题', '判断题', '填空题'], width='small'),
                    '题目': st.column_config.TextColumn('题目', width='large'),
                    '答案': st.column_config.TextColumn('答案', width='small'),
                    '解析': st.column_config.TextColumn('解析', width='medium'),
                },
                hide_index=True,
                key="suspicious_editor"
            )
            if st.button("💾 应用修改", type="secondary"):
                if view_mode == "仅可疑题目":
                    df.iloc[issue_indices] = edited_df.values
                else:
                    df = edited_df
                st.session_state.data = df
                st.success("修改已应用")
                st.rerun()
        else:
            st.success("✅ 未发现可疑题目，题型识别正常")

    if '题型' in df.columns:
        type_counts = df['题型'].value_counts()
        type_cols = st.columns(len(type_counts))
        for idx, (q_type, count) in enumerate(type_counts.items()):
            with type_cols[idx]:
                percentage = (count / total_questions) * 100
                st.metric(f"📊 {q_type}", f"{count}题", f"{percentage:.1f}%")

    col_back, col_save, col_practice = st.columns([1, 1, 2])

    with col_back:
        if st.button("返回修改", use_container_width=True):
            st.session_state.import_step = 'mapping'
            st.rerun()

    with col_save:
        if st.button("保存到题库库", type="primary", use_container_width=True):
            from database import save_question_bank, activate_question_bank, get_active_question_bank
            file_name = st.session_state.current_file_name or "未命名题库"
            bank_name = st.session_state.current_bank_name or file_name.split('.')[0]
            bank_id = save_question_bank(df, file_name, bank_name)

            if bank_id:
                activate_question_bank(bank_id)
                st.session_state.current_bank_name = bank_name
                st.session_state.current_bank_file = file_name
                st.session_state.current_bank_id = bank_id
                st.success(f"✅ 题库已保存: {bank_name} ({total_questions}题)")
                time.sleep(1)
                st.session_state.current_page = 'banks'
                st.rerun()
            else:
                st.error("保存题库失败")

    with col_practice:
        if st.button("直接开始刷题", type="primary", use_container_width=True):
            st.session_state.current_page = 'practice'
            st.rerun()

    st.divider()

    if st.button("📋 完成，返回仪表盘", type="secondary", use_container_width=True):
        st.session_state.current_page = 'dashboard'
        st.session_state.import_step = 'upload'
        st.rerun()
