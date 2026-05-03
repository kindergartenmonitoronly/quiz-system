"""
页面配置与 Session 状态初始化
"""
import streamlit as st


def setup_page_config():
    """Streamlit 页面配置"""
    st.set_page_config(
        page_title="智能刷题系统 Pro",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo',
            'Report a bug': 'https://github.com/your-repo/issues',
            'About': '智能刷题系统 v3.5'
        }
    )


def init_session_state():
    """初始化所有 session_state 变量"""
    defaults = {
        'current_index': 0,
        'show_result': False,
        'user_answer': None,
        'data': None,
        'original_data': None,
        'data_cleaned': False,
        'current_file_name': None,
        'column_mapping': {},
        'show_column_mapper': False,
        'mapping_warnings': [],
        'mapping_errors': [],

        # 键盘控制防抖相关
        'last_submit_time': 0,
        'last_keyboard_time': 0,
        # 幻影按钮相关
        'phantom_buttons_created': False,
        # 刷题设置
        'random_mode': False,
        'selected_types': [],
        'question_count': 20,
        'random_indices': [],
        'shuffle_mode': False,
        # 计时与状态
        'question_start_time': None,
        'time_limit': 30,
        'question_results': [],
        'quiz_completed': False,
        'quiz_active': False,
        'quiz_start_time': None,
        'quiz_end_time': None,
        # UI控制
        'sidebar_collapsed': False,
        'auto_timeout': False,
        'option_columns_count': 4,
        'preview_page': 0,
        'preview_page_size': 5,
        # 错题本模式
        'review_mode': False,
        'wrong_book_pagination': 1,
        'wrong_book_page_size': 10,
        'wrong_book_filter': None,
        'wrong_book_sort': 'error_count',
        'wrong_book_sort_display': '错误次数',
        # 导航状态
        'current_page': 'dashboard',
        'practice_mode': None,
        'import_step': 'upload',
        # 结算页面控制
        'force_exit_results': False,
        'final_quiz_time': None,
        # 题型分析结果
        'type_analysis': None,
        # 当前题库信息
        'current_bank_name': None,
        'current_bank_file': None,
        'current_bank_id': None,
        # 错题本练习前保存的原题库信息
        'original_bank_before_review': None,
        # 错题本随机模式
        'wrong_book_random_mode': False,
        # 错题本选中的文件列表
        'wrong_book_selected_files': [],
        # 导入状态重置标记
        'file_uploaded': False,
        # 答题卡显示控制
        'show_answer_card': False,
        # 学习进度相关
        'continue_progress': False,
        'current_progress_id': None,
        # 键盘控制相关
        'keyboard_control': True,
        'keyboard_focus_index': 0,
        'keyboard_selected_option': None,
        # 答题卡跳转
        'jump_to_question': None,
        'show_answer_card_detail': False,
        # 测试映射结果显示控制
        'show_test_mapping_result': False,
        'test_mapping_df': None,
        # 顺序刷题索引队列
        'quiz_queue_indices': None,
        'original_data_backup': None,
        # 庆祝状态
        'celebration_shown': False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
