"""
键盘导航控制模块
- 幻影按钮回调
- 键盘事件监听
- 滚轮支持
"""
import time
import json
import streamlit as st
import streamlit.components.v1 as components

from quiz_engine import (
    get_current_question_and_total, submit_answer_action,
    start_question_timer, is_question_answered, get_total_questions
)
from utils import get_key_profile


# ============================================================
# 幻影按钮回调函数
# ============================================================

def phantom_option_callback(option_index):
    """幻影按钮：数字键1-6选择选项"""
    if st.session_state.get('show_result', False):
        return

    if not st.session_state.get('quiz_active', False):
        return

    row, _ = get_current_question_and_total()
    if row is None:
        return

    q_type = row.get('题型', '单选题')

    current_time = time.time()
    last_key_time = st.session_state.get('last_keyboard_time', 0)
    if current_time - last_key_time < 0.1:
        return
    st.session_state.last_keyboard_time = current_time

    valid_option_indices = []
    for i in range(6):
        option_letter = chr(65 + i)
        option_col = f'选项{option_letter}'
        if option_col in row and str(row[option_col]).strip():
            valid_option_indices.append(i)

    if q_type == '判断题':
        valid_option_indices = [0, 1]

    if option_index not in valid_option_indices:
        show_keyboard_error_feedback(f"无效选项 {option_index + 1}")
        return

    if q_type in ['单选题', '判断题']:
        # 显示标签始终是 chr(65+option_index)，原始答案字母从打乱表获取
        display_letter = chr(65 + option_index)
        shuffle_key = f'_shuffle_{st.session_state.current_index}'
        if st.session_state.shuffle_mode and q_type == '单选题' and shuffle_key in st.session_state:
            shuffled_values = st.session_state[shuffle_key]
            if option_index < len(shuffled_values):
                original_letter = shuffled_values[option_index]
            else:
                return
        else:
            original_letter = display_letter

        # radio 值使用打乱后该位置的显示文本，user_answer 使用原始字母
        option_text = f"{display_letter}. {row[f'选项{original_letter}']}"
        st.session_state.user_answer = original_letter
        radio_key = f"q_{st.session_state.current_index}"
        st.session_state[radio_key] = option_text

    elif q_type == '多选题':
        # 打乱模式下：显示字母 = 按下的位置，需映射到原始字母
        option_letter = chr(65 + option_index)
        checkbox_key = f"mq_{option_letter}_{st.session_state.current_index}"
        current_state = st.session_state.get(checkbox_key, False)
        new_state = not current_state
        st.session_state[checkbox_key] = new_state

        # 构建用户答案：将选中的显示字母映射回原始字母
        letter_map = st.session_state.get(f'_shuffle_map_{st.session_state.current_index}', {})
        selected_letters = []
        for i in range(6):
            display_letter = chr(65 + i)
            key = f"mq_{display_letter}_{st.session_state.current_index}"
            if st.session_state.get(key, False):
                if letter_map and display_letter in letter_map:
                    selected_letters.append(letter_map[display_letter])
                else:
                    selected_letters.append(display_letter)

        st.session_state.user_answer = ''.join(sorted(selected_letters))


def phantom_exit_callback():
    """Esc 键：触发退出确认弹窗"""
    if not st.session_state.get('quiz_active', False):
        return
    st.session_state.show_exit_confirm = True


def phantom_enter_callback():
    """幻影按钮：Enter键提交答案"""
    if st.session_state.get('show_result', False):
        return

    if not st.session_state.get('quiz_active', False):
        return

    row, _ = get_current_question_and_total()
    if row is None:
        return

    if hasattr(st.session_state, 'last_submit_time'):
        current_time = time.time()
        if current_time - st.session_state.last_submit_time < 0.3:
            return
        st.session_state.last_submit_time = current_time
    else:
        st.session_state.last_submit_time = time.time()

    # 从 radio/checkbox/text 控件同步 user_answer（鼠标点击后 Enter 提交的关键修复）
    q_type = row.get('题型', '单选题')
    radio_key = f"q_{st.session_state.current_index}"
    if q_type in ['单选题', '判断题'] and radio_key in st.session_state:
        radio_val = st.session_state[radio_key]
        if radio_val and not st.session_state.user_answer:
            # 从 radio 显示文本提取选项字母
            st.session_state.user_answer = radio_val[0] if radio_val and radio_val[0] in 'ABCDEF' else radio_val
    elif q_type == '多选题':
        selected = []
        for i in range(6):
            letter = chr(65 + i)
            if st.session_state.get(f"mq_{letter}_{st.session_state.current_index}", False):
                # 打乱映射
                letter_map = st.session_state.get(f'_shuffle_map_{st.session_state.current_index}', {})
                selected.append(letter_map.get(letter, letter) if letter_map else letter)
        if selected:
            st.session_state.user_answer = ''.join(sorted(selected))

    submit_answer_action(row)


def phantom_prev_callback():
    """幻影按钮：向左键上一题"""
    if not st.session_state.get('quiz_active', False):
        return

    if st.session_state.current_index <= 0:
        return

    target_index = st.session_state.current_index - 1
    is_answered, result = is_question_answered(target_index)

    if is_answered:
        st.session_state.current_index = target_index
        st.session_state.show_result = True
        st.session_state.user_answer = result['user']
    else:
        if (not st.session_state.random_mode and
                not st.session_state.review_mode):
            return

        st.session_state.current_index = target_index
        st.session_state.show_result = False
        st.session_state.user_answer = None
        start_question_timer()


def phantom_next_callback():
    """幻影按钮：向右键下一题"""
    if not st.session_state.get('quiz_active', False):
        return

    total_q = get_total_questions()

    if st.session_state.current_index >= total_q - 1:
        return

    target_index = st.session_state.current_index + 1
    is_answered, result = is_question_answered(target_index)

    if is_answered:
        st.session_state.current_index = target_index
        st.session_state.show_result = True
        st.session_state.user_answer = result['user']
    else:
        if not st.session_state.show_result:
            return

        st.session_state.current_index = target_index
        st.session_state.show_result = False
        st.session_state.user_answer = None
        start_question_timer()


# ============================================================
# 键盘错误反馈
# ============================================================

def show_keyboard_error_feedback(message):
    """显示键盘操作错误反馈"""
    js_code = f"""
    <script>
    (function() {{
        const doc = window.parent.document;

        const existingError = doc.getElementById('keyboard-error-hint');
        if (existingError) {{
            existingError.remove();
        }}

        const errorDiv = document.createElement('div');
        errorDiv.id = 'keyboard-error-hint';
        errorDiv.innerHTML = `
            <div style="
                position: fixed;
                top: 80px;
                right: 30px;
                background: rgba(244, 67, 54, 0.9);
                color: white;
                padding: 8px 15px;
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
                z-index: 99999;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                backdrop-filter: blur(5px);
                animation: fadeInOut 1s ease-in-out;
                border: 1px solid rgba(255,255,255,0.2);
            ">
                ⚠️ {message}
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeInOut {{
                0% {{ opacity: 0; transform: translateY(-20px); }}
                20% {{ opacity: 1; transform: translateY(0); }}
                80% {{ opacity: 1; transform: translateY(0); }}
                100% {{ opacity: 0; transform: translateY(-20px); }}
            }}
        `;

        doc.head.appendChild(style);
        doc.body.appendChild(errorDiv);

        setTimeout(() => {{
            if (errorDiv.parentNode) {{
                errorDiv.parentNode.removeChild(errorDiv);
            }}
        }}, 1500);
    }})();
    </script>
    """
    components.html(js_code, height=0)


# ============================================================
# 滚轮支持
# ============================================================

def render_keyboard_controls():
    """渲染键盘控制JS代码 — 支持可配置快捷键"""
    if not st.session_state.get('quiz_active', False) or not st.session_state.get('keyboard_control', False):
        return

    profile = get_key_profile()
    kb_json = json.dumps(profile)

    js_code = """<script>
(function() {
    const doc = window.parent.document;
    let isProcessing = false;
    const KB = __KB_JSON__;

    function hidePhantomButtons() {
        const buttons = doc.querySelectorAll('button');
        buttons.forEach(function(btn) {
            if (btn.innerText && btn.innerText.indexOf(":::") >= 0) {
                btn.style.position = 'fixed'; btn.style.opacity = '0';
                btn.style.pointerEvents = 'none'; btn.style.zIndex = '-1';
                btn.style.left = '0'; btn.style.top = '0';
                btn.style.height = '1px'; btn.style.width = '1px';
                btn.style.overflow = 'hidden';
            }
        });
    }

    function clickByText(keyword) {
        try {
            var buttons = Array.from(doc.querySelectorAll('button'));
            var target = buttons.find(function(btn) {
                return btn.innerText && btn.innerText.indexOf(keyword) >= 0;
            });
            if (target) { target.click(); return true; }
            return false;
        } catch (err) { return false; }
    }

    var handleKeydown = function(e) {
        var activeTag = doc.activeElement.tagName;
        if (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT') {
            if (doc.activeElement.type === 'text') return;
        }

        var key = e.key;
        if (isProcessing) return;

        // 选择选项键
        var selIdx = KB.select.indexOf(key);
        if (selIdx >= 0) {
            e.preventDefault(); e.stopPropagation();
            isProcessing = true;
            clickByText(':::OPT_' + selIdx + ':::');
            highlightOptionFeedback(selIdx);
            setTimeout(function() { isProcessing = false; }, 50);
            return;
        }
        // 提交键
        if (KB.submit.indexOf(key) >= 0) {
            e.preventDefault(); e.stopPropagation();
            isProcessing = true;
            clickByText(':::NAV_ENTER:::');
            highlightEnterFeedback();
            setTimeout(function() { isProcessing = false; }, 100);
            return;
        }
        // 导航键 - 上一题
        if (KB.prev.indexOf(key) >= 0) {
            e.preventDefault(); e.stopPropagation();
            isProcessing = true;
            clickByText(':::NAV_PREV:::');
            highlightArrowFeedback(key);
            setTimeout(function() { isProcessing = false; }, 100);
            return;
        }
        // 导航键 - 下一题
        if (KB.next.indexOf(key) >= 0) {
            e.preventDefault(); e.stopPropagation();
            isProcessing = true;
            clickByText(':::NAV_NEXT:::');
            highlightArrowFeedback(key);
            setTimeout(function() { isProcessing = false; }, 100);
            return;
        }
        // 退出键
        if (KB.exit.indexOf(key) >= 0) {
            e.preventDefault(); e.stopPropagation();
            clickByText(':::NAV_EXIT:::');
            return;
        }
    };

    function highlightOptionFeedback(index) {
        var mainSection = doc.querySelector('section[data-testid="stMain"]');
        if (!mainSection) return;
        var radios = mainSection.querySelectorAll('div[data-testid="stRadio"] label');
        if (radios && index < radios.length) {
            var label = radios[index];
            var originalBg = label.style.backgroundColor;
            label.style.backgroundColor = '#e3f2fd';
            label.style.transition = 'background-color 0.3s';
            setTimeout(function() { label.style.backgroundColor = originalBg || ''; }, 300);
        }
        var checkboxes = mainSection.querySelectorAll('div[data-testid="stCheckbox"] label');
        if (checkboxes && index < checkboxes.length) {
            var label = checkboxes[index];
            var originalBg = label.style.backgroundColor;
            label.style.backgroundColor = '#e3f2fd';
            label.style.transition = 'background-color 0.3s';
            setTimeout(function() { label.style.backgroundColor = originalBg || ''; }, 300);
        }
        showFloatingHint('按键 ' + (index + 1));
    }

    function highlightEnterFeedback() {
        showFloatingHint('提交答案');
        var buttons = Array.from(doc.querySelectorAll('button'));
        var submitBtn = buttons.find(function(btn) {
            return btn.innerText && btn.innerText.indexOf('提交') >= 0;
        });
        if (submitBtn) {
            var bg = submitBtn.style.backgroundColor;
            submitBtn.style.backgroundColor = '#4CAF50';
            submitBtn.style.color = 'white';
            setTimeout(function() { submitBtn.style.backgroundColor = bg || ''; submitBtn.style.color = ''; }, 300);
        }
    }

    function highlightArrowFeedback(key) {
        var dir = KB.prev.indexOf(key) >= 0 ? '上一题' : '下一题';
        showFloatingHint(dir);
    }

    function showFloatingHint(text) {
        var existing = doc.getElementById('keyboard-feedback-hint');
        if (existing) existing.remove();
        var hint = doc.createElement('div');
        hint.id = 'keyboard-feedback-hint';
        hint.innerHTML = '<div style="position:fixed;top:100px;right:30px;background:rgba(76,175,80,0.9);color:white;padding:10px 20px;border-radius:20px;font-size:14px;font-weight:bold;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.2);backdrop-filter:blur(5px);animation:fadeInOut 1s ease-in-out;border:1px solid rgba(255,255,255,0.2)">🎮 ' + text + '</div>';
        var style = doc.createElement('style');
        style.textContent = '@keyframes fadeInOut { 0%{opacity:0;transform:translateY(-20px)} 20%{opacity:1;transform:translateY(0)} 80%{opacity:1;transform:translateY(0)} 100%{opacity:0;transform:translateY(-20px)} }';
        doc.head.appendChild(style);
        doc.body.appendChild(hint);
        setTimeout(function() { if (hint.parentNode) hint.parentNode.removeChild(hint); }, 1000);
    }

    function initKeyboard() {
        try {
            doc.removeEventListener('keydown', handleKeydown);
            doc.addEventListener('keydown', handleKeydown, { capture: true });
            hidePhantomButtons();
            if (!window.phantomObserver) {
                window.phantomObserver = new MutationObserver(function() { hidePhantomButtons(); });
                window.phantomObserver.observe(doc.body, { childList: true, subtree: true, attributes: true });
            }
        } catch (err) { console.error('键盘控制初始化失败:', err); }
    }

    setTimeout(function() { initKeyboard(); }, 1000);

    window.__cleanupPhantomKeyboard = function() {
        if (window.phantomObserver) { window.phantomObserver.disconnect(); window.phantomObserver = null; }
        doc.removeEventListener('keydown', handleKeydown);
    };

})();
</script>"""

    components.html(js_code.replace('__KB_JSON__', kb_json), height=0)
