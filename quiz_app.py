"""
智能刷题系统 Pro v3.7 — 主入口
"""
import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime
import streamlit.components.v1 as components

from config import setup_page_config, init_session_state
from database import (
    init_db, add_to_wrong_book, save_study_progress,
    save_study_stats_with_consistent_time, delete_wrong_question,
    get_all_question_banks, get_all_study_progress
)
from utils import format_time, truncate_filename, question_type_css
from quiz_engine import (
    start_quiz, submit_answer_action, restore_original_data,
    get_current_question_and_total, check_timeout_logic,
    render_js_timer, start_question_timer, get_total_questions
)
from keyboard import (
    phantom_option_callback, phantom_enter_callback,
    phantom_prev_callback, phantom_next_callback,
    render_keyboard_controls
)
from ui_components import render_answer_card
from views import (
    render_dashboard, render_import_page, render_bank_management,
    render_practice_page, render_progress_management,
    render_wrong_book_page, render_stats_page
)

# ============================================================
# 初始化
# ============================================================
setup_page_config()
init_db()
init_session_state()

# ============================================================
# CSS 样式
# ============================================================
st.markdown("""
<style>
.main-header { padding: 1rem 0; border-bottom: 2px solid #4CAF50; margin-bottom: 2rem; }
.question-card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
.correct-answer { color: #4CAF50; font-weight: bold; }
.wrong-answer { color: #f44336; font-weight: bold; }
.stButton > button { transition: all 0.3s ease; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
.filename-truncate { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.error-count-badge { display: inline-block; background: #ff5722; color: white; border-radius: 12px; padding: 2px 8px; font-size: 12px; margin-left: 5px; font-weight: bold; }

.answer-card-item { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 5px; margin: 2px; cursor: pointer; transition: all 0.3s ease; }
.answer-card-item:hover { transform: scale(1.1); }
.answer-card-correct { background: #4CAF50; color: white; }
.answer-card-wrong { background: #f44336; color: white; }

.keyboard-hint { background: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 8px 12px; margin: 10px 0; font-size: 14px; color: #1565c0; }
.keyboard-selected { background-color: #e3f2fd !important; border-color: #2196f3 !important; box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.3); transition: all 0.2s ease; }
.keyboard-shortcut { display: inline-block; background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; padding: 2px 6px; margin: 0 4px; font-size: 12px; font-family: monospace; color: #333; }
.keyboard-float-hint { position: fixed; bottom: 20px; right: 20px; background: rgba(0, 0, 0, 0.8); color: white; padding: 10px 15px; border-radius: 10px; font-size: 14px; z-index: 9999; max-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); backdrop-filter: blur(5px); border: 1px solid rgba(255,255,255,0.1); }

.light-info-box { background: #f8f9fa; border-radius: 10px; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; color: #333333; }
.light-warning-box { background: #fff3cd; border-radius: 10px; padding: 15px; margin: 10px 0; border-left: 4px solid #ffc107; color: #856404; }

.stDataFrame { width: 100% !important; max-width: 100% !important; }
div[data-testid="stDataFrame"] { width: 100% !important; }
div[data-testid="stDataFrameResizable"] { width: 100% !important; }

input[type="number"] { cursor: ns-resize; }

/* 题型色彩系统 */
.qtype-single { border-left: 4px solid #2196F3 !important; }
.qtype-multi  { border-left: 4px solid #9C27B0 !important; }
.qtype-judge  { border-left: 4px solid #FF9800 !important; }
.qtype-fill   { border-left: 4px solid #009688 !important; }
.qtype-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 12px; font-weight: bold; color: white; margin-left: 8px;
}

/* 隐藏幻影按钮 */
button[kind="secondaryFormSubmit"]:has-text(":::") {
    display: none !important; visibility: hidden !important; opacity: 0 !important;
    position: absolute !important; left: -9999px !important;
    width: 1px !important; height: 1px !important; overflow: hidden !important;
    pointer-events: none !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 退出确认弹窗
# ============================================================
@st.dialog("确认提前结束答题")
def exit_confirm_dialog():
    """提前结束答题的确认弹窗"""
    st.warning("⚠️ 确认提前结束答题吗？当前进度将会保存。")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ 保存进度并退出", type="primary", use_container_width=True):
            _save_and_exit_quiz()
            st.rerun()

    with col2:
        if st.button("❌ 不保存直接退出", type="secondary", use_container_width=True):
            st.session_state.quiz_active = False
            st.session_state.quiz_completed = False
            restore_original_data()
            st.rerun()

    with col3:
        if st.button("↩️ 取消", use_container_width=True):
            st.rerun()


def _save_and_exit_quiz():
    """保存进度并退出刷题"""
    if st.session_state.current_bank_id and st.session_state.practice_mode:
        save_study_progress(
            bank_id=st.session_state.current_bank_id,
            practice_mode=st.session_state.practice_mode,
            current_index=st.session_state.current_index,
            question_results=st.session_state.question_results,
            total_questions=get_total_questions(),
            is_completed=False
        )
        st.success("进度已保存")

    st.session_state.quiz_active = False
    st.session_state.quiz_completed = False
    restore_original_data()


# ============================================================
# 侧边栏导航
# ============================================================
with st.sidebar:
    # ================================================================
    # 答题模式 — 精简侧边栏
    # ================================================================
    if st.session_state.quiz_active and not st.session_state.quiz_completed:
        st.markdown("## 🎯 正在答题")

        if st.session_state.current_bank_name:
            st.caption(f"题库: {truncate_filename(st.session_state.current_bank_name, 15)}")

        row, total_q = get_current_question_and_total()
        if row and total_q:
            progress_pct = (st.session_state.current_index + 1) / total_q
            st.progress(progress_pct, text=f"进度 {st.session_state.current_index + 1}/{total_q}")
            if '题型' in row:
                st.caption(f"当前题型: {row['题型']}")

        st.divider()

        if st.button("🏠 退出刷题", use_container_width=True, type="secondary"):
            if st.session_state.current_bank_id and st.session_state.practice_mode:
                save_study_progress(
                    bank_id=st.session_state.current_bank_id,
                    practice_mode=st.session_state.practice_mode,
                    current_index=st.session_state.current_index,
                    question_results=st.session_state.question_results,
                    total_questions=get_total_questions()
                )
                st.success("进度已自动保存")

            st.session_state.quiz_active = False
            st.session_state.sidebar_collapsed = False
            st.rerun()

    # ================================================================
    # 非答题模式 — 完整侧边栏
    # ================================================================
    else:
        st.markdown("## 🎯 功能导航")
        st.divider()

        page_options = {
            'dashboard': '🏠 仪表盘',
            'import': '📂 导入题库',
            'banks': '📚 题库管理',
            'practice': '📖 开始刷题',
            'progress': '📋 学习进度',
            'wrong_book': '📕 错题本',
            'stats': '📈 学习统计'
        }

        current_page = st.radio(
            "选择功能",
            options=list(page_options.keys()),
            format_func=lambda x: page_options[x],
            index=list(page_options.keys()).index(st.session_state.current_page)
        )

        if current_page != st.session_state.current_page:
            if st.session_state.quiz_active and st.session_state.quiz_completed:
                if st.session_state.current_bank_id and st.session_state.practice_mode:
                    save_study_progress(
                        bank_id=st.session_state.current_bank_id,
                        practice_mode=st.session_state.practice_mode,
                        current_index=st.session_state.current_index,
                        question_results=st.session_state.question_results,
                        total_questions=get_total_questions(),
                        is_completed=st.session_state.quiz_completed
                    )

                st.session_state.quiz_active = False
                st.session_state.quiz_completed = False
                st.session_state.force_exit_results = True
                if 'final_quiz_time' in st.session_state:
                    del st.session_state.final_quiz_time

            st.session_state.current_page = current_page
            st.rerun()

        st.divider()

        st.markdown("### 📊 系统状态")

        if st.session_state.current_bank_name:
            bank_name = st.session_state.current_bank_name
            display_name = truncate_filename(bank_name, 15)
            st.metric("当前题库", display_name)
            if st.session_state.data is not None:
                st.caption(f"{len(st.session_state.data)}题")

        banks = get_all_question_banks()
        if banks:
            st.caption(f"共{len(banks)}个题库")

        progress_list = get_all_study_progress()
        if progress_list:
            st.metric("未完成进度", f"{len(progress_list)}个")

        # 题型分布（侧边栏精简显示）
        if st.session_state.data is not None and '题型' in st.session_state.data.columns:
            type_counts = st.session_state.data['题型'].value_counts()
            if len(type_counts) > 0:
                type_colors = {'单选题': '#2196F3', '多选题': '#9C27B0', '判断题': '#FF9800', '填空题': '#009688'}
                total = type_counts.sum()
                for qtype, count in type_counts.items():
                    pct = count / total
                    color = type_colors.get(qtype, '#757575')
                    st.markdown(
                        f'<div style="display:flex;align-items:center;margin:4px 0;font-size:13px">'
                        f'<span style="width:12px;height:12px;border-radius:3px;background:{color};margin-right:8px"></span>'
                        f'{qtype} {count}题'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        st.divider()

        st.markdown("### ⚡ 快捷操作")

        if st.button("🔄 刷新页面", use_container_width=True):
            st.rerun()

# ============================================================
# 主界面 — 答题模式
# ============================================================
if st.session_state.quiz_active and not st.session_state.force_exit_results:
    if st.session_state.keyboard_control:
        render_keyboard_controls()
        st.markdown("""
        <div class="keyboard-float-hint">
            <div style="font-weight: bold; margin-bottom: 5px;">🎮 键盘控制已启用</div>
            <div style="font-size: 12px; opacity: 0.9;">
                <div>数字键1-6: 选择选项</div>
                <div>Enter: 提交答案</div>
                <div>← →: 切换题目</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 结果结算页
    if st.session_state.quiz_completed:
        results = st.session_state.question_results

        if results:
            if not st.session_state.get('celebration_shown', False):
                st.balloons()
                st.session_state.celebration_shown = True

            st.header("🎉 测验完成！")

            if st.button("📋 查看答题卡", type="primary"):
                st.session_state.show_answer_card = True

            if st.session_state.show_answer_card:
                render_answer_card()
                st.divider()

            correct_count = sum(1 for r in results if r['is_correct'])
            total_count = len(results)
            score = int(correct_count / total_count * 100) if total_count > 0 else 0

            if 'final_quiz_time' not in st.session_state or st.session_state.final_quiz_time is None:
                if st.session_state.quiz_start_time:
                    st.session_state.final_quiz_time = time.time() - st.session_state.quiz_start_time
                else:
                    st.session_state.final_quiz_time = 0

            total_time = st.session_state.final_quiz_time
            save_study_stats_with_consistent_time(total_count, correct_count)

            if st.session_state.current_bank_id and st.session_state.practice_mode:
                save_study_progress(
                    bank_id=st.session_state.current_bank_id,
                    practice_mode=st.session_state.practice_mode,
                    current_index=st.session_state.current_index,
                    question_results=st.session_state.question_results,
                    total_questions=get_total_questions(),
                    is_completed=True
                )

            formatted_time = format_time(total_time)

            # 可视化：环形图 + 用时柱状图
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure(data=[go.Pie(
                        labels=['正确', '错误'],
                        values=[correct_count, total_count - correct_count],
                        hole=0.6,
                        marker_colors=['#4CAF50', '#f44336'],
                        textinfo='none'
                    )])
                    fig.update_layout(
                        title=f'正确率 {score}%', title_x=0.5, title_font_size=16,
                        height=280, margin=dict(t=40, b=10, l=10, r=10),
                        showlegend=True, legend=dict(orientation='h', y=-0.1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.metric("正确率", f"{score}%")

            with col_chart2:
                if results:
                    time_data = pd.DataFrame([
                        {'题号': i + 1, '用时(秒)': r['time']}
                        for i, r in enumerate(results)
                    ])
                    st.bar_chart(time_data.set_index('题号'), use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总题数", total_count)
            col2.metric("正确数", correct_count)
            col3.metric("正确率", f"{score}%")
            col4.metric("总耗时", formatted_time)

            with st.expander("📋 详细报告", expanded=True):
                report_df = pd.DataFrame(results)
                report_df['状态'] = report_df['is_correct'].apply(lambda x: '✅ 正确' if x else '❌ 错误')
                st.dataframe(
                    report_df[['index', 'question', 'user', 'correct', '状态', 'time']],
                    use_container_width=True,
                    column_config={
                        'index': '题号', 'question': '题目',
                        'user': '你的答案', 'correct': '正确答案',
                        '状态': '状态', 'time': '用时(秒)'
                    }
                )

            wrong_results = [r for r in results if not r['is_correct']]
            if wrong_results:
                st.subheader("📝 错题分析")
                for r in wrong_results:
                    st.error(f"第{r['index'] + 1}题: {r['question'][:50]}...")
        else:
            st.header("📝 测验已结束")
            st.info("您没有回答任何题目")
            if 'final_quiz_time' not in st.session_state or st.session_state.final_quiz_time is None:
                if st.session_state.quiz_start_time:
                    st.session_state.final_quiz_time = time.time() - st.session_state.quiz_start_time
                else:
                    st.session_state.final_quiz_time = 0
            total_time = st.session_state.final_quiz_time
            formatted_time = format_time(total_time)
            st.metric("总耗时", formatted_time)

        col_back, col_retry, col_export = st.columns(3)
        with col_back:
            if st.button("🏠 返回主页", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.sidebar_collapsed = False
                st.session_state.force_exit_results = False
                st.session_state.show_answer_card = False
                st.session_state.celebration_shown = False
                if 'final_quiz_time' in st.session_state:
                    del st.session_state.final_quiz_time
                st.rerun()

        with col_retry:
            if st.button("🔄 重新练习", use_container_width=True):
                st.session_state.force_exit_results = False
                st.session_state.show_answer_card = False
                st.session_state.celebration_shown = False
                if 'final_quiz_time' in st.session_state:
                    del st.session_state.final_quiz_time
                start_quiz('random' if st.session_state.random_mode else 'sequential')
                st.rerun()

        with col_export:
            if results:
                if st.button("📥 导出报告", use_container_width=True):
                    report_df = pd.DataFrame(results)
                    csv = report_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "下载CSV", csv,
                        f"测验报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )

    # 答题页
    else:
        df = st.session_state.data

        row, total_q = get_current_question_and_total()

        if row is None:
            st.error("无法获取题目数据")
            st.rerun()

        is_timeout_check = check_timeout_logic()
        if is_timeout_check and not st.session_state.show_result:
            submit_answer_action(row)
            st.rerun()

        with st.container():
            st.markdown(f'<div class="question-card qtype-{question_type_css(row)}">', unsafe_allow_html=True)

            col_info1, col_info2, col_timer = st.columns([6, 2, 2])
            with col_info1:
                if '题号' in row and str(row['题号']).strip():
                    original_number = row['题号']
                    if isinstance(original_number, (int, float)):
                        display_number = f"Q{int(original_number)}"
                    else:
                        display_number = f"Q{original_number}" if not str(original_number).startswith('Q') else str(original_number)
                    st.markdown(f"### {display_number}")
                else:
                    st.markdown(f"### Q{st.session_state.current_index + 1}")
                st.markdown(f"**{row['题目']}**")

            with col_info2:
                st.metric("进度", f"{st.session_state.current_index + 1}/{total_q}")
                type_key = question_type_css(row)
                type_colors = {'single': '#2196F3', 'multi': '#9C27B0', 'judge': '#FF9800', 'fill': '#009688'}
                st.markdown(
                    f'<span class="qtype-badge" style="background:{type_colors.get(type_key, "#2196F3")}">{row["题型"]}</span>',
                    unsafe_allow_html=True
                )

            with col_timer:
                if not st.session_state.show_result:
                    render_js_timer()

            if st.session_state.keyboard_control and not st.session_state.show_result:
                st.markdown("""
                <style>
                .keyboard-hint-compact { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 10px 15px; margin: 0 0 15px 0; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.15); border: 1px solid rgba(255,255,255,0.2); font-size: 13px; }
                .keyboard-hint-header { font-size: 14px; font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; justify-content: center; gap: 8px; }
                .keyboard-hint-keys { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; }
                .keyboard-key-item { display: flex; align-items: center; gap: 4px; }
                .keyboard-key-badge { background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; padding: 1px 6px; font-size: 11px; font-family: 'Monaco', 'Menlo', monospace; color: white; min-width: 40px; text-align: center; }
                .keyboard-key-label { font-size: 11px; opacity: 0.9; }
                </style>
                """, unsafe_allow_html=True)

                if st.session_state.keyboard_control and st.session_state.quiz_active:
                    st.markdown("""
                    <div class="keyboard-hint-compact">
                        <div class="keyboard-hint-header"><span>🎮 键盘控制已启用</span></div>
                        <div class="keyboard-hint-keys">
                            <div class="keyboard-key-item"><span class="keyboard-key-badge">1-6</span><span class="keyboard-key-label">选择选项</span></div>
                            <div class="keyboard-key-item"><span class="keyboard-key-badge">Enter</span><span class="keyboard-key-label">提交答案</span></div>
                            <div class="keyboard-key-item"><span class="keyboard-key-badge">← →</span><span class="keyboard-key-label">切换题目</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            user_choice = None
            disabled = st.session_state.show_result or st.session_state.auto_timeout

            q_type = row.get('题型', '单选题')

            if q_type in ['单选题', '判断题']:
                opts = []
                option_values = []

                if q_type == '判断题':
                    opts = ['A. 正确', 'B. 错误']
                    option_values = ['A', 'B']
                else:
                    for i in range(st.session_state.option_columns_count):
                        val = row.get(f'选项{chr(65 + i)}', '').strip()
                        if val:
                            opts.append(f"{chr(65 + i)}. {val}")
                            option_values.append(chr(65 + i))

                if st.session_state.shuffle_mode and q_type == '单选题':
                    combined = list(zip(opts, option_values))
                    random.shuffle(combined)
                    opts, option_values = zip(*combined) if combined else ([], [])

                val = st.radio("请选择答案:", opts,
                               key=f"q_{st.session_state.current_index}",
                               disabled=disabled, index=None)

                if val:
                    idx = opts.index(val)
                    user_choice = option_values[idx]

            elif q_type == '多选题':
                st.write("**多选题 (可多选):**")
                choices = []
                options = []

                for i in range(st.session_state.option_columns_count):
                    val = row.get(f'选项{chr(65 + i)}', '').strip()
                    if val:
                        options.append((chr(65 + i), val))

                if st.session_state.shuffle_mode:
                    random.shuffle(options)

                for opt_key, opt_val in options:
                    if st.checkbox(f"{opt_key}. {opt_val}",
                                   key=f"mq_{opt_key}_{st.session_state.current_index}",
                                   disabled=disabled):
                        choices.append(opt_key)

                if choices:
                    user_choice = "".join(sorted(choices))

            elif q_type == '填空题':
                user_choice = st.text_input("请输入答案:",
                                            key=f"t_{st.session_state.current_index}",
                                            disabled=disabled,
                                            placeholder="在此输入答案")

            st.markdown("</div>", unsafe_allow_html=True)

            # 幻影按钮区域（键盘控制用）
            if st.session_state.get('keyboard_control', False) and st.session_state.get('quiz_active', False):
                with st.container():
                    for i in range(6):
                        st.button(
                            f":::OPT_{i}:::",
                            key=f"phantom_opt_{i}_{st.session_state.current_index}",
                            on_click=phantom_option_callback,
                            args=(i,),
                            help=f"键盘按键{i + 1}",
                            disabled=st.session_state.get('show_result', False),
                        )
                    st.button(
                        ":::NAV_PREV:::",
                        key=f"phantom_prev_{st.session_state.current_index}",
                        on_click=phantom_prev_callback,
                        disabled=not st.session_state.get('show_result', False),
                    )
                    st.button(
                        ":::NAV_NEXT:::",
                        key=f"phantom_next_{st.session_state.current_index}",
                        on_click=phantom_next_callback,
                        disabled=not st.session_state.get('show_result', False),
                    )
                    st.button(
                        ":::NAV_ENTER:::",
                        key=f"phantom_enter_{st.session_state.current_index}",
                        on_click=phantom_enter_callback,
                        disabled=st.session_state.get('show_result', False),
                    )

            # 操作按钮
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

            if not st.session_state.show_result:
                with col_btn1:
                    if st.button("✅ 提交答案", type="primary", use_container_width=True):
                        st.session_state.user_answer = user_choice
                        submit_answer_action(row)
                        st.rerun()

                with col_btn2:
                    if st.button("⏭️ 跳过本题", type="secondary", use_container_width=True):
                        if st.session_state.current_index < total_q - 1:
                            st.session_state.current_index += 1
                            start_question_timer()
                            st.rerun()

                with col_btn3:
                    if st.button("🏁 提前结束", type="secondary", key="early_exit_btn", use_container_width=True):
                        exit_confirm_dialog()
            else:
                st.divider()

                is_correct = False
                correct_ans = str(row['答案']).strip()
                user_ans = st.session_state.user_answer

                if q_type == '多选题':
                    is_correct = (''.join(sorted(str(user_ans))) == ''.join(sorted(correct_ans)))
                else:
                    is_correct = (str(user_ans).upper() == correct_ans.upper())

                if is_correct:
                    st.success("🎉 **回答正确！**")
                else:
                    if st.session_state.auto_timeout:
                        st.error("⏰ **时间到！**")
                    else:
                        st.error("❌ **回答错误**")

                    st.markdown(f"**你的答案:** {user_ans}")
                    st.markdown(f"**正确答案:** {correct_ans}")

                explanation = row.get('解析', '').strip()
                if explanation:
                    with st.expander("📝 查看解析", expanded=True):
                        st.info(explanation)

                if st.session_state.review_mode and '_db_id' in row:
                    if st.button("✅ 已掌握，移出错题本"):
                        if delete_wrong_question(row['_db_id']):
                            st.success("已从错题本移除")
                            time.sleep(1)
                            st.rerun()

                col_prev, col_next, col_end = st.columns([1, 2, 1])

                with col_prev:
                    if st.session_state.current_index > 0:
                        if st.button("⬅️ 上一题", type="secondary", use_container_width=True):
                            st.session_state.current_index -= 1
                            st.session_state.show_result = False
                            st.session_state.user_answer = None
                            st.session_state.auto_timeout = False
                            start_question_timer()
                            st.rerun()

                with col_next:
                    if st.session_state.current_index < total_q - 1:
                        if st.button("➡️ 下一题", type="primary", use_container_width=True):
                            st.session_state.current_index += 1
                            st.session_state.show_result = False
                            st.session_state.user_answer = None
                            st.session_state.auto_timeout = False
                            start_question_timer()
                            st.rerun()
                    else:
                        if st.button("🏁 完成测验", type="primary", use_container_width=True):
                            st.session_state.quiz_completed = True
                            st.rerun()

                with col_end:
                    if st.button("🏁 提前结束", type="secondary", key="early_exit_btn2", use_container_width=True):
                        exit_confirm_dialog()

# ============================================================
# 主界面 — 页面路由
# ============================================================
else:
    if st.session_state.current_page == 'dashboard':
        render_dashboard()
    elif st.session_state.current_page == 'import':
        render_import_page()
    elif st.session_state.current_page == 'banks':
        render_bank_management()
    elif st.session_state.current_page == 'practice':
        render_practice_page()
    elif st.session_state.current_page == 'progress':
        render_progress_management()
    elif st.session_state.current_page == 'wrong_book':
        render_wrong_book_page()
    elif st.session_state.current_page == 'stats':
        render_stats_page()

# 页脚
st.markdown("---")
st.caption("智能刷题系统 Pro v3.7 | © 2024 | 技术支持: AI Assistant | 已修复键盘控制和表格宽度问题")
