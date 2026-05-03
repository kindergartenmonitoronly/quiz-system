"""
通用 UI 组件模块
- 数据预览
- 题目渲染
- 答题卡
"""
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components


def render_preview_table(df, truncate_chars=3, show_all=True):
    """渲染数据预览"""
    st.markdown("""
        <style>
        .preview-table td { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .preview-table th { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        </style>
    """, unsafe_allow_html=True)

    display_df = df.copy()
    display_df = display_df.fillna('')

    if show_all:
        display_df = display_df.head(5)
        for col in display_df.columns:
            display_df[col] = display_df[col].astype(str).apply(
                lambda x: x[:truncate_chars] + '..' if len(x) > truncate_chars else x
            )
        st.dataframe(display_df, use_container_width=True)
        st.caption(f"预览前5行（每单元格最多显示{truncate_chars}个字符），共{len(df)}行数据")
    else:
        if '题型' in display_df.columns:
            question_types = display_df['题型'].unique()
            preview_samples = []
            for q_type in question_types:
                type_samples = display_df[display_df['题型'] == q_type]
                if len(type_samples) > 0:
                    sample = type_samples.sample(1).iloc[0]
                    preview_samples.append(sample)

            if preview_samples:
                preview_df = pd.DataFrame(preview_samples)
                for col in preview_df.columns:
                    preview_df[col] = preview_df[col].astype(str).apply(
                        lambda x: x[:truncate_chars] + '..' if len(x) > truncate_chars else x
                    )
                st.dataframe(preview_df, use_container_width=True)
                st.caption(f"每种题型预览1题（共{len(preview_df)}题），共{len(df)}行数据")
            else:
                st.info("暂无数据可预览")
        else:
            for col in display_df.columns:
                display_df[col] = display_df[col].astype(str).apply(
                    lambda x: x[:truncate_chars] + '..' if len(x) > truncate_chars else x
                )
            st.dataframe(display_df.head(5), use_container_width=True)
            st.caption(f"预览前5行（每单元格最多显示{truncate_chars}个字符），共{len(df)}行数据")


def render_unified_question(row, show_result=False, user_answer=None, correct_answer=None,
                            is_correct=None, is_detail_view=False, question_index=None):
    """统一渲染题目"""
    with st.container():
        st.markdown('<div class="question-card">', unsafe_allow_html=True)

        col_info1, col_info2 = st.columns([6, 2])
        with col_info1:
            if question_index is not None:
                if '题号' in row and str(row['题号']).strip():
                    original_number = row['题号']
                    if isinstance(original_number, (int, float)):
                        display_number = f"Q{int(original_number)}"
                    else:
                        display_number = f"Q{original_number}" if not str(original_number).startswith('Q') else str(original_number)
                    st.markdown(f"### {display_number}")
                else:
                    st.markdown(f"### Q{question_index + 1}")
            else:
                if '题号' in row and str(row['题号']).strip():
                    original_number = row['题号']
                    if isinstance(original_number, (int, float)):
                        display_number = f"Q{int(original_number)}"
                    else:
                        display_number = f"Q{original_number}" if not str(original_number).startswith('Q') else str(original_number)
                    st.markdown(f"### {display_number}")
                else:
                    st.markdown(f"### ")
            st.markdown(f"**{row['题目']}**")

        with col_info2:
            if not is_detail_view:
                st.metric("题型", row['题型'])
            else:
                st.caption(f"题型: {row['题型']}")

        st.divider()

        q_type = row.get('题型', '单选题')

        if q_type in ['单选题', '判断题']:
            opts = []
            if q_type == '判断题':
                opts = ['A. 正确', 'B. 错误']
            else:
                for i in range(st.session_state.option_columns_count):
                    val = row.get(f'选项{chr(65 + i)}', '').strip()
                    if val:
                        opts.append(f"{chr(65 + i)}. {val}")

            if show_result and is_detail_view:
                for opt in opts:
                    st.write(opt)
            elif not is_detail_view:
                st.radio("请选择答案:", opts,
                         key=f"q_{question_index}" if not is_detail_view else f"detail_radio_{question_index}",
                         disabled=show_result or is_detail_view, index=None)

        elif q_type == '多选题':
            st.write("**多选题 (可多选):**")
            options = []
            for i in range(st.session_state.option_columns_count):
                val = row.get(f'选项{chr(65 + i)}', '').strip()
                if val:
                    options.append((chr(65 + i), val))

            if show_result and is_detail_view:
                for opt_key, opt_val in options:
                    st.write(f"{opt_key}. {opt_val}")
            elif not is_detail_view:
                for opt_key, opt_val in options:
                    st.checkbox(f"{opt_key}. {opt_val}",
                                key=f"mq_{opt_key}_{question_index}" if not is_detail_view else f"detail_check_{opt_key}_{question_index}",
                                disabled=show_result or is_detail_view)

        elif q_type == '填空题':
            if is_detail_view:
                st.write("**填空题**")
            elif not is_detail_view:
                st.text_input("请输入答案:",
                              key=f"t_{question_index}" if not is_detail_view else f"detail_text_{question_index}",
                              disabled=show_result or is_detail_view, placeholder="在此输入答案")

        if show_result and user_answer is not None and correct_answer is not None:
            st.divider()
            if is_correct:
                st.success("🎉 **回答正确！**")
            else:
                st.error("❌ **回答错误**")
            st.markdown(f"**你的答案:** {user_answer}")
            st.markdown(f"**正确答案:** {correct_answer}")

            explanation = row.get('解析', '').strip()
            if explanation:
                with st.expander("📝 查看解析", expanded=True):
                    st.info(explanation)

        st.markdown("</div>", unsafe_allow_html=True)


def find_question_in_dataframe(df, question_text):
    """在DataFrame中查找题目"""
    if df is None or df.empty:
        return None

    question_text_clean = str(question_text).strip()

    mask = df['题目'].astype(str).str.strip() == question_text_clean
    if mask.any():
        return df[mask].iloc[0]

    if len(question_text_clean) > 100:
        question_part = question_text_clean[:100]
        for idx, row in df.iterrows():
            if str(row['题目']).strip().startswith(question_part):
                return row

    return None


def find_question_by_mode(result_index, question_text):
    """根据刷题模式查找题目"""
    row = None

    if hasattr(st.session_state, 'random_mode') and st.session_state.random_mode:
        if hasattr(st.session_state, 'random_indices') and result_index < len(st.session_state.random_indices):
            original_idx = st.session_state.random_indices[result_index]
            if st.session_state.data is not None:
                row = st.session_state.data.loc[original_idx]
    elif hasattr(st.session_state, 'quiz_queue_indices') and st.session_state.quiz_queue_indices and result_index < len(st.session_state.quiz_queue_indices):
        original_idx = st.session_state.quiz_queue_indices[result_index]
        if st.session_state.data is not None:
            row = st.session_state.data.loc[original_idx]

    return row


def setup_answer_card_interaction():
    """设置答题卡交互的JavaScript代码"""
    js_code = """
    <script>
    window.answerCardClickHandler = function(index) {
        window.parent.postMessage({
            'type': 'streamlit:setComponentValue',
            'value': index,
            'key': 'answer_card_index'
        }, '*');
    };
    </script>
    """
    components.html(js_code, height=0)


def render_answer_card_detail_enhanced():
    """增强的答题卡详情页面"""
    if not st.session_state.question_results or st.session_state.jump_to_question is None:
        return

    result_index = st.session_state.jump_to_question
    if result_index < 0 or result_index >= len(st.session_state.question_results):
        st.error("题目索引无效")
        return

    result = st.session_state.question_results[result_index]

    st.subheader(f"📋 第{result_index + 1}题详情")

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if result_index > 0:
            if st.button("⬅️ 上一题", use_container_width=True):
                st.session_state.jump_to_question = result_index - 1
                st.rerun()

    with col_nav2:
        if st.button("📋 返回答题卡", use_container_width=True):
            st.session_state.show_answer_card_detail = False
            st.session_state.jump_to_question = None
            st.rerun()

    with col_nav3:
        if result_index < len(st.session_state.question_results) - 1:
            if st.button("➡️ 下一题", use_container_width=True):
                st.session_state.jump_to_question = result_index + 1
                st.rerun()

    row = None

    if hasattr(st.session_state, 'original_data_backup'):
        df = st.session_state.original_data_backup
        row = find_question_in_dataframe(df, result['question'])

    if row is None and st.session_state.data is not None:
        df = st.session_state.data
        row = find_question_in_dataframe(df, result['question'])

    if row is None:
        row = find_question_by_mode(result_index, result['question'])

    if row is not None:
        render_unified_question(
            row, show_result=True, user_answer=result['user'],
            correct_answer=result['correct'], is_correct=result['is_correct'],
            is_detail_view=True, question_index=result_index
        )
    else:
        st.warning("无法加载原题内容，但答题记录如下：")
        st.write(f"**题目:** {result['question'][:200]}...")
        st.write(f"**你的答案:** {result['user']}")
        st.write(f"**正确答案:** {result['correct']}")
        st.write(f"**结果:** {'✅ 正确' if result['is_correct'] else '❌ 错误'}")
        st.write(f"**用时:** {result['time']}秒")

    st.divider()
    col_extra1, col_extra2, col_extra3 = st.columns([1, 2, 1])

    with col_extra1:
        if result_index > 0:
            if st.button("⬅️ 上一题 (底部)", key=f"prev_bottom_{result_index}", use_container_width=True):
                st.session_state.jump_to_question = result_index - 1
                st.rerun()

    with col_extra2:
        st.caption(f"第 {result_index + 1} / {len(st.session_state.question_results)} 题")
        new_index = st.number_input(
            "跳转到题目:", min_value=1, max_value=len(st.session_state.question_results),
            value=result_index + 1, key=f"jump_input_{result_index}", help="输入题号后按回车跳转"
        )
        if new_index - 1 != result_index:
            st.session_state.jump_to_question = new_index - 1
            st.rerun()

    with col_extra3:
        if result_index < len(st.session_state.question_results) - 1:
            if st.button("➡️ 下一题 (底部)", key=f"next_bottom_{result_index}", use_container_width=True):
                st.session_state.jump_to_question = result_index + 1
                st.rerun()


def render_answer_card():
    """渲染答题卡"""
    setup_answer_card_interaction()
    if not st.session_state.question_results:
        return

    st.subheader("📋 答题卡")

    if st.session_state.show_answer_card_detail and st.session_state.jump_to_question is not None:
        render_answer_card_detail_enhanced()
        return

    results = st.session_state.question_results
    total = len(results)

    cols_per_row = 10
    rows = (total + cols_per_row - 1) // cols_per_row

    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col in range(cols_per_row):
            idx = row * cols_per_row + col
            if idx < total:
                result = results[idx]
                with cols[col]:
                    if result['is_correct']:
                        badge_color = "#4CAF50"
                        badge_text = f"{idx + 1} ✅"
                    else:
                        badge_color = "#f44336"
                        badge_text = f"{idx + 1} ❌"

                    badge_html = f"""
                    <div style='
                        background: {badge_color}; color: white;
                        border-radius: 5px; padding: 5px;
                        text-align: center; cursor: pointer;
                        margin: 2px; transition: all 0.2s ease;
                    '>
                        {badge_text}
                    </div>
                    """
                    components.html(badge_html, height=50)

    if st.button("刷新答题卡状态", key="refresh_answer_card", type="secondary", use_container_width=True):
        st.rerun()

    st.divider()

    correct_count = sum(1 for r in results if r['is_correct'])
    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("总题数", total_count)
    with col_stat2:
        st.metric("正确数", correct_count)
    with col_stat3:
        st.metric("正确率", f"{accuracy:.1f}%")

    st.subheader("详细答题情况")

    for idx, result in enumerate(results):
        with st.container():
            col_status, col_content, col_action = st.columns([1, 3, 1])

            with col_status:
                if result['is_correct']:
                    st.success(f"第{idx + 1}题 ✅")
                else:
                    st.error(f"第{idx + 1}题 ❌")

            with col_content:
                st.write(f"**题目:** {result['question'][:100]}...")
                st.write(f"**你的答案:** {result['user']}")
                st.write(f"**正确答案:** {result['correct']}")
                st.write(f"**用时:** {result['time']}秒")

            with col_action:
                if st.button("查看详情", key=f"view_detail_{idx}"):
                    st.session_state.jump_to_question = idx
                    st.session_state.show_answer_card_detail = True
                    st.rerun()

            if idx < len(results) - 1:
                st.divider()
