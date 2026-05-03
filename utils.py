"""
工具函数模块
- 时间格式化
- 答案标准化
- 题型识别
- 数据清洗
- 模板下载
- 随机算法
"""
import re
import base64
import random
import pandas as pd
from collections import Counter
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# 时间格式化
# ============================================================

def format_time(total_seconds):
    """将秒数格式化为易读的时间字符串"""
    total_seconds = int(total_seconds)

    if total_seconds <= 0:
        return "0秒"

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}秒")

    return "".join(parts)


# ============================================================
# 答案标准化
# ============================================================

def normalize_answer(answer):
    """统一答案格式"""
    if pd.isna(answer):
        return ''

    s = str(answer).strip()

    judge_map = {
        '正确': 'A', '对': 'A', '√': 'A', '是': 'A', 'TRUE': 'A', 'YES': 'A', 'T': 'A',
        '正确✓': 'A', '√正确': 'A', '对✓': 'A', '✓': 'A', '对√': 'A', '是✓': 'A',
        '正确的': 'A', '对的': 'A', '是的': 'A', '真': 'A', '真确': 'A', '正确无误': 'A',
        '错误': 'B', '错': 'B', '×': 'B', '否': 'B', 'FALSE': 'B', 'NO': 'B', 'F': 'B',
        '错误×': 'B', '×错误': 'B', '错×': 'B', '否×': 'B',
        '错误的': 'B', '错的': 'B', '不是': 'B', '不对': 'B', '不': 'B', '不正确': 'B',
    }

    if s in judge_map:
        return judge_map[s]

    s_upper = s.upper()
    if s_upper in judge_map:
        return judge_map[s_upper]

    s_lower = s.lower()
    judge_patterns = {
        'true': 'A', 'yes': 'A', 't': 'A', 'right': 'A', 'correct': 'A',
        'false': 'B', 'no': 'B', 'f': 'B', 'wrong': 'B', 'incorrect': 'B'
    }

    if s_lower in judge_patterns:
        return judge_patterns[s_lower]

    s_clean = re.sub(r'[()（）\s]', '', s_upper)
    found = re.findall(r'[A-F]', s_clean)
    if found:
        return ''.join(sorted(set(found)))

    return s


# ============================================================
# 题型识别
# ============================================================

def detect_all_question_types(row):
    """题型识别逻辑 - 基于题目特征的精确识别算法"""
    q = str(row.get('题目', ''))
    a = str(row.get('答案', ''))

    type_keywords = {
        '单选题': ['[单选]', '(单选)', '【单选】', '[单选题]', '（单选题）', '单选题', '单项选择', '单选', '单项'],
        '多选题': ['[多选]', '(多选)', '【多选】', '[多选题]', '（多选题）', '多选题', '多项选择', '多选', '多项', '不定项'],
        '判断题': ['[判断]', '(判断)', '【判断】', '[判断题]', '（判断题）', '判断题', '判断正误', '判断'],
        '填空题': ['[填空]', '(填空)', '【填空】', '[填空题]', '（填空题）', '填空题', '填空']
    }

    for q_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in q:
                return q_type

    valid_opts = 0
    opt_contents = {}
    for c in 'ABCDEF':
        opt_val = str(row.get(f'选项{c}', '')).strip()
        if opt_val and opt_val not in ['', 'nan', 'None']:
            valid_opts += 1
            opt_contents[c] = opt_val

    norm_a = normalize_answer(a)

    if valid_opts == 2 and norm_a in ['A', 'B']:
        if 'A' in opt_contents and 'B' in opt_contents:
            opt_a = opt_contents['A']
            opt_b = opt_contents['B']
            judge_pairs = [
                ('正确', '错误'), ('对', '错'), ('√', '×'), ('是', '否'),
                ('True', 'False'), ('Yes', 'No'), ('对的', '错的'),
                ('正确无误', '错误明显'), ('正确✓', '错误×')
            ]
            for pair in judge_pairs:
                if (pair[0] in opt_a and pair[1] in opt_b) or (pair[1] in opt_a and pair[0] in opt_b):
                    return '判断题'

    if len(norm_a) > 1 and all(char in 'ABCDEF' for char in norm_a):
        if valid_opts >= len(norm_a):
            answer_has_content = True
            for char in norm_a:
                if char not in opt_contents:
                    answer_has_content = False
                    break
            if answer_has_content:
                multi_keywords = ['哪些', '哪几个', '哪几项', '多选', '多项', '不止一个', '多个',
                                  '可以包括', '可能包括', '包括以下', '包含以下', '正确的有', '包括', '包含',
                                  '哪几项', '哪几个是', '哪些是']
                if any(keyword in q for keyword in multi_keywords):
                    return '多选题'
                for opt in opt_contents.values():
                    if '全选' in opt or '以上都是' in opt or '全部' in opt:
                        return '多选题'
                return '多选题'

    if valid_opts == 0:
        fill_patterns = [
            r'_{3,}', r'_{2,}',
            r'（\s*）', r'\(\s*\)', r'【\s*】', r'\[\s*\]',
        ]
        for pattern in fill_patterns:
            if re.search(pattern, q):
                return '填空题'

        if q.startswith('()') or q.startswith('（）'):
            if norm_a and norm_a in 'ABCDEF':
                return '单选题' if len(norm_a) == 1 else '多选题'
            else:
                return '填空题'

        if a and a.strip():
            return '填空题'

    if len(norm_a) == 1 and norm_a in 'ABCDEF' and valid_opts >= 2:
        if norm_a in opt_contents:
            return '单选题'

    if valid_opts >= 2:
        return '单选题'
    elif valid_opts == 1:
        if norm_a and norm_a not in 'ABCDEF':
            return '填空题'
        else:
            return '单选题'
    else:
        return '填空题'


# ============================================================
# 数据清洗
# ============================================================

def clean_question_data(df, mapping):
    """数据清洗 - 优先使用题型映射列"""
    if df is None or df.empty:
        return pd.DataFrame()

    new_df = pd.DataFrame()

    cols = ['题号', '题型', '题目', '答案', '解析'] + [f'选项{chr(65 + i)}' for i in
                                                       range(st.session_state.option_columns_count)]

    for std_col in cols:
        orig_col = mapping.get(std_col, '[不映射]')
        if orig_col != '[不映射]' and orig_col in df.columns:
            new_df[std_col] = df[orig_col]
        else:
            new_df[std_col] = ''

    new_df = new_df.fillna('').astype(str)

    for col in new_df.columns:
        new_df[col] = new_df[col].str.strip()

    new_df['答案'] = new_df['答案'].apply(normalize_answer)

    if '题型' in new_df.columns:
        has_type_content = new_df['题型'].str.strip().ne('').any()
        if not has_type_content:
            new_df['题型'] = new_df.apply(detect_all_question_types, axis=1)
        else:
            type_mapping = {
                '单选': '单选题', '单选题': '单选题', '单': '单选题', '单项': '单选题',
                '多选': '多选题', '多选题': '多选题', '多': '多选题', '多项': '多选题',
                '判断': '判断题', '判断题': '判断题', '判断正误': '判断题',
                '填空': '填空题', '填空题': '填空题', '填空': '填空题',
            }

            def normalize_question_type(q_type):
                q_type_str = str(q_type).strip()
                if not q_type_str:
                    return ''
                for key, value in type_mapping.items():
                    if key in q_type_str:
                        return value
                return q_type_str

            new_df['题型'] = new_df['题型'].apply(normalize_question_type)

            empty_mask = new_df['题型'].str.strip() == ''
            if empty_mask.any():
                new_df.loc[empty_mask, '题型'] = new_df[empty_mask].apply(detect_all_question_types, axis=1)
    else:
        new_df['题型'] = new_df.apply(detect_all_question_types, axis=1)

    filtered_df = new_df[new_df['题目'].str.strip() != ''].reset_index(drop=True)

    if '题号' in filtered_df.columns:
        if filtered_df['题号'].str.strip().eq('').all():
            filtered_df['题号'] = range(1, len(filtered_df) + 1)

    if not filtered_df.empty:
        st.session_state.type_analysis = analyze_question_types(filtered_df)

    return filtered_df


def validate_data(df):
    """验证数据质量"""
    warnings = []

    if df.empty:
        warnings.append("数据为空")
        return warnings

    duplicates = df['题目'].duplicated().sum()
    if duplicates > 0:
        warnings.append(f"发现 {duplicates} 个重复题目")

    missing_answers = df['答案'].str.strip().eq('').sum()
    if missing_answers > 0:
        warnings.append(f"发现 {missing_answers} 个题目缺少答案")

    if '题型' in df.columns:
        type_counts = df['题型'].value_counts()
        for q_type, count in type_counts.items():
            warnings.append(f"题型 '{q_type}': {count} 题")

    for i in range(st.session_state.option_columns_count):
        option_col = f'选项{chr(65 + i)}'
        if option_col in df.columns:
            empty_options = df[option_col].str.strip().eq('').sum()
            if empty_options > 0 and empty_options < len(df):
                warnings.append(f"选项{chr(65 + i)} 有 {empty_options} 个为空")

    return warnings


def check_mapping_duplicates(mapping):
    """检查映射是否有重复"""
    errors = []

    mapped_values = [v for v in mapping.values() if v != '[不映射]']
    value_counts = Counter(mapped_values)
    duplicates = [value for value, count in value_counts.items() if count > 1]

    for dup in duplicates:
        fields = [k for k, v in mapping.items() if v == dup]
        errors.append(f"⚠️ 列 '{dup}' 被重复映射到: {', '.join(fields)}")

    required_fields = ['题目', '答案']
    for field in required_fields:
        if field not in mapping or mapping.get(field) == '[不映射]':
            errors.append(f"❌ 必需字段 '{field}' 未映射")

    return errors


def auto_match_columns(df_columns):
    """自动匹配列名"""
    mapping = {}
    patterns = {
        '题号': ['题号', '序号', '编号', 'id', 'ID', '题目编号', '题目序号'],
        '题型': ['题型', '题目类型', '题目类别', '类型', 'question_type', 'type', '题型分类'],
        '题目': ['题目', '问题', 'question', '题干', '题目内容', '试题', '题目描述'],
        '答案': ['答案', 'answer', '正确答案', '参考答案', '标准答案', '答案内容'],
        '解析': ['解析', '讲解', 'explanation', '答案解析', '试题解析', '解析说明'],
    }

    for i in range(6):
        letter = chr(65 + i)
        patterns[f'选项{letter}'] = [f'选项{letter}', f'option{letter}', f'选择{letter}', f'{letter}',
                                     f'选项{i + 1}', f'选项 {letter}', f'Option{letter}', f'选择 {letter}']

    for std_col, patterns_list in patterns.items():
        found = False
        for pattern in patterns_list:
            for idx, col in enumerate(df_columns):
                if pattern.lower() in col.lower():
                    mapping[std_col] = df_columns[idx]
                    found = True
                    break
            if found:
                break

        if not found and std_col in ['题目', '答案']:
            mapping[std_col] = df_columns[0] if df_columns else '[不映射]'
        elif not found:
            mapping[std_col] = '[不映射]'

    return mapping


# ============================================================
# 题型分析
# ============================================================

def analyze_question_types(df):
    """分析题库题型分布"""
    if df is None or df.empty:
        return {}

    analysis = {
        'total': len(df),
        'type_counts': df['题型'].value_counts().to_dict(),
        'type_percentages': {},
        'sample_by_type': {},
        'detailed_stats': {},
        'potential_issues': []
    }

    for q_type, count in analysis['type_counts'].items():
        analysis['type_percentages'][q_type] = (count / analysis['total']) * 100

    for q_type in df['题型'].unique():
        type_df = df[df['题型'] == q_type]
        if len(type_df) > 0:
            sample = type_df.iloc[0]
            analysis['sample_by_type'][q_type] = {
                '题目': sample['题目'][:100] + '...' if len(sample['题目']) > 100 else sample['题目'],
                '答案': sample['答案'],
                '有效选项数': sum(
                    1 for c in 'ABCDEF' if str(sample.get(f'选项{c}', '')).strip() not in ['', 'nan', 'None'])
            }

    for q_type in df['题型'].unique():
        type_df = df[df['题型'] == q_type]
        analysis['detailed_stats'][q_type] = {
            'count': len(type_df),
            'avg_answer_length': type_df['答案'].str.len().mean() if len(type_df) > 0 else 0,
            'has_explanation': type_df['解析'].str.strip().ne('').sum() if '解析' in type_df.columns else 0
        }

    analysis['potential_issues'] = find_potential_misclassified(df)
    return analysis


def find_potential_misclassified(df):
    """查找可能被误判的题目"""
    issues = []

    for idx, row in df.iterrows():
        q = str(row.get('题目', ''))
        a = str(row.get('答案', ''))
        detected_type = row.get('题型', '未知')

        valid_opts = 0
        for c in 'ABCDEF':
            opt_val = str(row.get(f'选项{c}', '')).strip()
            if opt_val and opt_val not in ['', 'nan', 'None']:
                valid_opts += 1

        norm_a = normalize_answer(a)
        issue = None

        if detected_type == '填空题' and valid_opts > 0 and norm_a and all(char in 'ABCDEF' for char in norm_a):
            issue = f"第{idx + 1}行: 题目有选项和答案({norm_a})，但被识别为填空题"
        elif detected_type == '单选题' and len(norm_a) > 1 and all(char in 'ABCDEF' for char in norm_a):
            issue = f"第{idx + 1}行: 答案有多个字母({norm_a})，但被识别为单选题"
        elif detected_type == '多选题' and len(norm_a) == 1:
            issue = f"第{idx + 1}行: 答案只有一个字母({norm_a})，但被识别为多选题"
        elif detected_type == '判断题' and valid_opts > 2:
            issue = f"第{idx + 1}行: 有{valid_opts}个选项，但被识别为判断题"

        if issue:
            q_preview = q[:50] + '...' if len(q) > 50 else q
            issue += f"\n      题目: {q_preview}"
            issues.append(issue)

    return issues


# ============================================================
# 随机算法
# ============================================================

def generate_random_indices(df, count, selected_types):
    """生成混合比例且保证各题型覆盖的随机索引"""
    filtered_df = df[df['题型'].isin(selected_types)]
    if len(filtered_df) == 0:
        return []

    indices = []
    groups = filtered_df.groupby('题型')
    remaining_pool = []

    for name, group in groups:
        if not group.empty:
            picked = group.sample(1)
            indices.extend(picked.index.tolist())
            remaining_pool.extend(group.drop(picked.index).index.tolist())

    needed = count - len(indices)
    if needed > 0 and remaining_pool:
        if len(remaining_pool) >= needed:
            extra = random.sample(remaining_pool, needed)
            indices.extend(extra)
        else:
            indices.extend(remaining_pool)

    random.shuffle(indices)
    return indices


# ============================================================
# 模板下载
# ============================================================

def create_template_download():
    """创建包含题号和题型列的综合模板"""
    full_template_data = {
        '题号': [1, 2, 3, 4],
        '题型': ['单选题', '多选题', '判断题', '填空题'],
        '题目': [
            'Python是一种什么样的语言？',
            '下列哪些是Python的特点？',
            'Python是编译型语言吗？',
            'Python的创始人是____'
        ],
        '答案': ['A', 'ABC', 'B', 'Guido van Rossum'],
        '选项A': ['一种高级编程语言', '简单易学', '正确', ''],
        '选项B': ['一种数据库系统', '开源免费', '错误', ''],
        '选项C': ['一种操作系统', '跨平台', '', ''],
        '选项D': ['一种硬件设备', '编译型语言', '', ''],
        '选项E': ['', '', '', ''],
        '选项F': ['', '', '', ''],
        '解析': [
            'Python是一种解释型、面向对象、动态数据类型的高级程序设计语言',
            'Python是解释型语言，不是编译型语言',
            'Python是解释型语言，不是编译型语言',
            'Guido van Rossum于1989年发明Python'
        ]
    }

    template_df = pd.DataFrame(full_template_data)
    column_order = ['题号', '题型', '题目', '答案', '选项A', '选项B', '选项C',
                    '选项D', '选项E', '选项F', '解析']
    column_order = [col for col in column_order if col in template_df.columns]
    return template_df[column_order]


def download_template(template_df, template_name="综合题库模板"):
    """提供模板下载"""
    csv = template_df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{template_name}.csv" style="text-decoration:none; color:inherit;">📥 {template_name}</a>'
    return href


# ============================================================
# 显示工具函数
# ============================================================

def truncate_filename(filename, max_length=25):
    """截断长文件名，用于显示"""
    if not filename:
        return "未命名"

    if len(filename) <= max_length:
        return filename

    name_parts = filename.split('.')
    if len(name_parts) > 1:
        name = '.'.join(name_parts[:-1])
        ext = name_parts[-1]
        if len(name) > max_length - 5:
            return name[:max_length - 8] + '...' + name[-5:] + '.' + ext
        else:
            return filename
    else:
        return filename[:max_length - 3] + '...'


def add_wheel_support():
    """全局鼠标滚轮支持：在所有数字输入框上滚动即模拟点击 +/- 按钮，触发 on_change 同步滑块"""
    components.html("""
    <script>
    (function() {
        const doc = window.parent.document;
        let wheelThrottle = false;

        function setupWheelListeners() {
            const inputs = doc.querySelectorAll('input[type="number"]');
            inputs.forEach(function(input) {
                if (input.dataset.wheelReady) return;
                input.dataset.wheelReady = '1';

                input.addEventListener('wheel', function(e) {
                    e.preventDefault();
                    e.stopPropagation();

                    if (wheelThrottle) return;
                    wheelThrottle = true;

                    const container = input.closest('[data-testid="stNumberInput"]');
                    if (!container) { wheelThrottle = false; return; }

                    const upBtn = container.querySelector('button[data-testid="stNumberInputStepUp"]');
                    const downBtn = container.querySelector('button[data-testid="stNumberInputStepDown"]');

                    const target = e.deltaY < 0 ? upBtn : downBtn;
                    if (target && !target.disabled) {
                        target.click();
                        // 视觉反馈
                        input.style.boxShadow = e.deltaY < 0
                            ? '0 0 0 2px #4CAF50'
                            : '0 0 0 2px #ff9800';
                        setTimeout(function() { input.style.boxShadow = ''; }, 200);
                    }

                    setTimeout(function() { wheelThrottle = false; }, 80);
                }, { passive: false });
            });
        }

        // 初次启动 + MutationObserver 覆盖动态添加的输入框
        setTimeout(setupWheelListeners, 800);
        new MutationObserver(function() { setTimeout(setupWheelListeners, 400); })
            .observe(doc.body, { childList: true, subtree: true });
    })();
    </script>
    """, height=0)
