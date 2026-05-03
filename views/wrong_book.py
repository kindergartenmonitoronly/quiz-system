"""错题本页面"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime

from database import (
    get_wrong_book_files, get_wrong_questions, delete_wrong_question,
    clear_wrong_book_by_filter, get_active_question_bank
)
from quiz_engine import start_quiz
from utils import truncate_filename


def start_review_sequential():
    """顺序重练错题"""
    filter_to_use = st.session_state.get('wrong_book_filter', None)
    wrong_list = get_wrong_questions(file_filter=filter_to_use, sort_by='recent_random')

    if not wrong_list:
        st.warning("没有符合条件的错题")
        return

    wrong_df = pd.DataFrame(wrong_list)
    st.session_state.data = wrong_df
    st.session_state.current_file_name = "错题重练"
    st.session_state.current_bank_name = "错题重练"
    st.session_state.review_mode = True
    st.session_state.wrong_book_random_mode = False

    if '题型' in wrong_df.columns:
        all_types = wrong_df['题型'].unique()
        st.session_state.selected_types = list(all_types)

    if not st.session_state.original_bank_before_review:
        active_bank = get_active_question_bank()
        if active_bank:
            st.session_state.original_bank_before_review = {
                'id': active_bank['id'],
                'name': active_bank['bank_name'],
                'file': active_bank['file_name']
            }

    start_quiz('review')
    st.rerun()


def start_review_random():
    """随机重练错题"""
    filter_to_use = st.session_state.get('wrong_book_filter', None)
    wrong_list = get_wrong_questions(file_filter=filter_to_use, sort_by='random')

    if not wrong_list:
        st.warning("没有符合条件的错题")
        return

    wrong_df = pd.DataFrame(wrong_list)
    st.session_state.data = wrong_df
    st.session_state.current_file_name = "错题重练"
    st.session_state.current_bank_name = "错题重练"
    st.session_state.review_mode = True
    st.session_state.wrong_book_random_mode = True

    if '题型' in wrong_df.columns:
        all_types = wrong_df['题型'].unique()
        st.session_state.selected_types = list(all_types)

    max_questions = min(20, len(wrong_df))
    st.session_state.question_count = min(10, max_questions) if max_questions > 1 else 1

    if not st.session_state.original_bank_before_review:
        active_bank = get_active_question_bank()
        if active_bank:
            st.session_state.original_bank_before_review = {
                'id': active_bank['id'],
                'name': active_bank['bank_name'],
                'file': active_bank['file_name']
            }

    start_quiz('review')
    st.rerun()


def start_error_count_review():
    """按错误次数排序刷题"""
    filter_to_use = st.session_state.get('wrong_book_filter', None)
    wrong_list = get_wrong_questions(file_filter=filter_to_use, sort_by='error_count_random')

    if not wrong_list:
        st.warning("没有符合条件的错题")
        return

    wrong_df = pd.DataFrame(wrong_list)
    st.session_state.data = wrong_df
    st.session_state.current_file_name = "错题重练"
    st.session_state.current_bank_name = "错题重练"
    st.session_state.review_mode = True
    st.session_state.wrong_book_random_mode = False

    if '题型' in wrong_df.columns:
        all_types = wrong_df['题型'].unique()
        st.session_state.selected_types = list(all_types)

    if not st.session_state.original_bank_before_review:
        active_bank = get_active_question_bank()
        if active_bank:
            st.session_state.original_bank_before_review = {
                'id': active_bank['id'],
                'name': active_bank['bank_name'],
                'file': active_bank['file_name']
            }

    start_quiz('review')
    st.rerun()


def render_wrong_book_page():
    """渲染错题本页面"""
    wrong_files = get_wrong_book_files()

    st.header("📕 错题本")

    col_sort, col_filter, col_stats = st.columns([1, 2, 1])

    with col_sort:
        sort_options_mapping = {
            "错误次数": "error_count",
            "最近错误": "recent",
        }
        sort_display_mapping = {v: k for k, v in sort_options_mapping.items()}

        current_sort = st.session_state.get('wrong_book_sort', 'error_count')
        if current_sort not in sort_display_mapping:
            current_sort = 'error_count'
        current_display = sort_display_mapping.get(current_sort, "错误次数")

        display_options = list(sort_options_mapping.keys())
        default_index = 0
        for idx, option in enumerate(display_options):
            if sort_options_mapping[option] == current_sort:
                default_index = idx
                break

        sort_option = st.selectbox("排序方式", display_options, index=default_index, key="wrong_book_sort_select")
        selected_sort = sort_options_mapping[sort_option]
        if selected_sort != st.session_state.wrong_book_sort:
            st.session_state.wrong_book_sort = selected_sort
            st.session_state.wrong_book_sort_display = sort_option

    with col_filter:
        if wrong_files:
            filter_options = ['全部'] + wrong_files
            default_index = 0
            if st.session_state.wrong_book_filter:
                for idx, option in enumerate(filter_options):
                    if option == st.session_state.wrong_book_filter:
                        default_index = idx
                        break

            selected_filter = st.selectbox("按题库筛选", filter_options, index=default_index, key="wrong_book_filter_select")
            st.session_state.wrong_book_filter = None if selected_filter == '全部' else selected_filter
        else:
            st.session_state.wrong_book_filter = None
            st.selectbox("按题库筛选", ["全部"], index=0, key="wrong_book_filter_select", disabled=True)

    with col_stats:
        filter_to_use = st.session_state.wrong_book_filter if hasattr(st.session_state, 'wrong_book_filter') else None
        wrong_list = get_wrong_questions(
            file_filter=filter_to_use,
            sort_by=st.session_state.wrong_book_sort
        )
        st.metric("当前错题", f"{len(wrong_list)} 道")
        if filter_to_use:
            st.caption(f"来自: {filter_to_use}")

    col_refresh, col_clear, col_empty = st.columns([1, 1, 2])

    with col_refresh:
        if st.button("🔄 刷新错题本", key="refresh_wrong_book"):
            st.rerun()

    with col_clear:
        if len(wrong_list) > 0:
            if st.button("🗑️ 清空当前筛选错题", key="clear_filtered_wrong", type="secondary"):
                with st.container():
                    st.warning("⚠️ 确认清空当前筛选条件下的错题吗？")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("确认清空", key="confirm_clear", type="primary"):
                            deleted_count = clear_wrong_book_by_filter(
                                file_filter=filter_to_use,
                                question_types=st.session_state.selected_types if hasattr(st.session_state, 'selected_types') else None
                            )
                            if deleted_count > 0:
                                st.success(f"已清空 {deleted_count} 道错题")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("没有需要清空的错题")
                    with col_cancel:
                        if st.button("取消", key="cancel_clear"):
                            st.rerun()
        else:
            st.button("🗑️ 清空当前筛选错题", key="clear_filtered_wrong_disabled", type="secondary", disabled=True)

    with col_empty:
        st.empty()

    if len(wrong_list) > 0:
        types_count = {}
        total_error_count = 0
        for q in wrong_list:
            q_type = q.get('题型', '未知')
            types_count[q_type] = types_count.get(q_type, 0) + 1
            total_error_count += q.get('_error_count', 1)

        st.subheader("📊 错题统计")
        col_stat1, col_stat2, col_stat3 = st.columns(3)

        with col_stat1:
            st.metric("错题数量", f"{len(wrong_list)} 道")
        with col_stat2:
            st.metric("总错误次数", f"{total_error_count} 次")
        with col_stat3:
            avg_errors = total_error_count / len(wrong_list) if len(wrong_list) > 0 else 0
            st.metric("平均错误次数", f"{avg_errors:.1f} 次/题")

        st.subheader("📈 题型分布")
        if types_count:
            type_cols = st.columns(len(types_count))
            for idx, (q_type, count) in enumerate(types_count.items()):
                with type_cols[idx]:
                    st.metric(q_type, count)
        else:
            st.info("暂无题型分布数据")

        st.subheader("🚀 操作")
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)

        with action_col1:
            if st.button("顺序重练", type="primary", use_container_width=True, key="start_review_sequential"):
                start_review_sequential()

        with action_col2:
            if st.button("随机重练", type="primary", use_container_width=True, key="start_review_random"):
                start_review_random()

        with action_col3:
            if st.button("按错误次数刷题", type="primary", use_container_width=True, key="start_review_error_count"):
                start_error_count_review()

        with action_col4:
            if len(wrong_list) > 0:
                export_df = pd.DataFrame(wrong_list)
                internal_fields = ['_db_id', '_file_name', '_added_time', '_error_count', '_first_wrong_time', '_last_wrong_time']
                for field in internal_fields:
                    if field in export_df.columns:
                        export_df = export_df.drop(columns=[field])

                st.download_button(
                    "📥 导出CSV",
                    export_df.to_csv(index=False).encode('utf-8-sig'),
                    f"错题本_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.button("📥 导出CSV", disabled=True, use_container_width=True)

        st.subheader("📝 错题列表")
        sort_display = st.session_state.get('wrong_book_sort_display', '错误次数')
        st.caption(f"排序方式: {sort_display}")

        page_size = st.session_state.wrong_book_page_size
        total_pages = max(1, (len(wrong_list) + page_size - 1) // page_size)

        page_col1, page_col2 = st.columns([1, 3])
        with page_col1:
            page = st.number_input("页码", 1, total_pages, 1, key="wrong_page_input")
        with page_col2:
            st.caption(f"共{total_pages}页，{len(wrong_list)}道错题")

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        current_page_questions = wrong_list[start_idx:end_idx]

        for idx, q in enumerate(current_page_questions, start=start_idx + 1):
            with st.container():
                file_info = ""
                if '_file_name' in q and q['_file_name']:
                    file_info = f" | 来源: {q['_file_name']}"

                error_count = q.get('_error_count', 1)
                if error_count > 1:
                    error_badge = f"<span class='error-count-badge'>{error_count}次</span>"
                    st.markdown(f"**{idx}. {q['题目'][:80]}...** {error_badge}", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{idx}. {q['题目'][:80]}...**")

                col_info, col_action = st.columns([4, 1])
                with col_info:
                    st.caption(f"题型: {q.get('题型', '未知')}{file_info}")
                    if '_first_wrong_time' in q and '_last_wrong_time' in q:
                        st.caption(f"首次错误: {q['_first_wrong_time']} | 最近错误: {q['_last_wrong_time']}")
                with col_action:
                    if st.button("删除", key=f"del_{q['_db_id']}"):
                        if delete_wrong_question(q['_db_id']):
                            st.success("删除成功")
                            time.sleep(0.5)
                            st.rerun()
                st.divider()
    else:
        st.info("暂无错题记录")
        st.markdown("""
        ### 💡 提示
        - 在刷题过程中答错的题目会自动添加到错题本
        - 同一题目多次答错会增加错误次数，不会重复记录
        - 错题本中的题目可以专门进行重练
        - 答对后可以从错题本中移除
        - 错题按来源文件进行分类管理
        """)
