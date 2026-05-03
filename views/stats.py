"""学习统计页面"""
import streamlit as st
import pandas as pd

from database import get_daily_summary


def render_stats_page():
    """渲染学习统计页面"""
    st.header("📈 学习统计")

    daily_df = get_daily_summary()

    if not daily_df.empty:
        daily_df = daily_df[daily_df['total_questions'] > 0]

        total_questions = daily_df['total_questions'].sum()
        total_correct = daily_df['correct_answers'].sum()
        avg_accuracy = daily_df['accuracy'].mean() if total_questions > 0 else 0
        total_time = daily_df['total_time'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总题数", total_questions)
        col2.metric("总正确数", total_correct)
        col3.metric("平均正确率", f"{avg_accuracy:.1f}%")
        col4.metric("总学习时间", f"{total_time // 60}分{total_time % 60}秒")

        st.subheader("📅 每日学习记录")
        display_df = daily_df.copy()

        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')

        display_df['accuracy'] = display_df['accuracy'].round(1)
        display_df = display_df.rename(columns={
            'date': '日期',
            'total_questions': '总题数',
            'correct_answers': '正确数',
            'accuracy': '正确率%',
            'total_time': '用时(秒)'
        })

        display_df = display_df.sort_values('日期', ascending=False)
        st.dataframe(display_df, use_container_width=True)

        if len(daily_df) > 1:
            st.subheader("📊 正确率趋势（按日期）")

            chart_data = daily_df[['date', 'accuracy']].copy()
            chart_data['date'] = pd.to_datetime(chart_data['date'])
            chart_data = chart_data.sort_values('date')
            chart_data = chart_data.set_index('date')

            st.line_chart(chart_data, use_container_width=True)

            if 'total_questions' in daily_df.columns:
                st.subheader("🔥 学习强度热力图")

                intensity_data = daily_df[['date', 'total_questions']].copy()
                intensity_data['date'] = pd.to_datetime(intensity_data['date'])
                intensity_data = intensity_data.sort_values('date')
                intensity_data = intensity_data.set_index('date')

                st.bar_chart(intensity_data, use_container_width=True)
    else:
        st.info("暂无学习历史数据")
        st.markdown("""
        ### 📊 统计说明
        - 系统会自动记录每次刷题的数据并按日汇总
        - 可以查看正确率趋势和学习强度
        - 数据保存30天
        - 横坐标为学习日期，按时间顺序排列
        """)
