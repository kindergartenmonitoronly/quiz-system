"""
键盘导航控制模块
- 幻影按钮回调
- 键盘事件监听
- 滚轮支持
"""
import time
import streamlit as st
import streamlit.components.v1 as components

from quiz_engine import (
    get_current_question_and_total, submit_answer_action,
    start_question_timer, is_question_answered
)


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
        option_letter = chr(65 + option_index)
        option_text = f"{option_letter}. {row[f'选项{option_letter}']}"
        st.session_state.user_answer = option_letter
        radio_key = f"q_{st.session_state.current_index}"
        st.session_state[radio_key] = option_text

    elif q_type == '多选题':
        option_letter = chr(65 + option_index)
        checkbox_key = f"mq_{option_letter}_{st.session_state.current_index}"
        current_state = st.session_state.get(checkbox_key, False)
        new_state = not current_state
        st.session_state[checkbox_key] = new_state

        selected_letters = []
        for i in range(6):
            letter = chr(65 + i)
            key = f"mq_{letter}_{st.session_state.current_index}"
            if st.session_state.get(key, False):
                selected_letters.append(letter)

        st.session_state.user_answer = ''.join(sorted(selected_letters))


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

    if st.session_state.random_mode:
        total_q = len(st.session_state.random_indices)
    elif hasattr(st.session_state, 'quiz_queue_indices') and st.session_state.quiz_queue_indices:
        total_q = len(st.session_state.quiz_queue_indices)
    else:
        total_q = len(st.session_state.data)

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

def add_enhanced_wheel_support():
    """增强的鼠标滚轮支持"""
    js_code = """
    <script>
    (function() {
        const setupEnhancedWheelSupport = () => {
            const doc = window.parent.document;
            let isProcessing = false;

            const handleWheel = (e) => {
                if (isProcessing) return;

                const input = e.target;
                if (input.type !== 'number') return;

                const container = input.closest('[data-testid="stNumberInput"]');
                if (!container) return;

                if (!container.querySelector('input[data-testid*="stNumberInput"]')) {
                    return;
                }

                e.preventDefault();
                e.stopPropagation();

                isProcessing = true;

                const step = parseInt(input.step) || 1;
                const max = parseInt(input.max) || 100;
                const min = parseInt(input.min) || 1;
                const currentValue = parseInt(input.value) || min;

                const delta = Math.sign(e.deltaY) * -1;

                let newValue = currentValue + (delta * step);
                newValue = Math.max(min, Math.min(max, newValue));

                if (newValue !== currentValue) {
                    input.value = newValue;

                    const event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);

                    input.style.boxShadow = '0 0 0 2px #4CAF50';
                    setTimeout(() => {
                        input.style.boxShadow = '';
                    }, 200);
                }

                setTimeout(() => {
                    isProcessing = false;
                }, 50);
            };

            const inputs = doc.querySelectorAll('input[type="number"]');
            inputs.forEach(input => {
                input.removeEventListener('wheel', handleWheel);
                input.addEventListener('wheel', handleWheel, { passive: false });
            });
        };

        setTimeout(setupEnhancedWheelSupport, 1000);

        const observer = new MutationObserver(() => {
            setTimeout(setupEnhancedWheelSupport, 500);
        });

        const doc = window.parent.document;
        observer.observe(doc.body, { childList: true, subtree: true });
    })();
    </script>
    """
    components.html(js_code, height=0)


def render_keyboard_controls():
    """渲染键盘控制JS代码 - 幻影按钮方案"""
    if not st.session_state.get('quiz_active', False) or not st.session_state.get('keyboard_control', False):
        return

    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            let isProcessing = false;

            function hidePhantomButtons() {
                const buttons = doc.querySelectorAll('button');
                buttons.forEach(btn => {
                    if (btn.innerText && btn.innerText.includes(":::")) {
                        btn.style.position = 'fixed';
                        btn.style.opacity = '0';
                        btn.style.pointerEvents = 'none';
                        btn.style.zIndex = '-1';
                        btn.style.left = '0';
                        btn.style.top = '0';
                        btn.style.height = '1px';
                        btn.style.width = '1px';
                        btn.style.overflow = 'hidden';
                    }
                });
            }

            function clickByText(keyword) {
                try {
                    const buttons = Array.from(doc.querySelectorAll('button'));
                    const target = buttons.find(btn =>
                        btn.innerText && btn.innerText.includes(keyword)
                    );
                    if (target) {
                        target.click();
                        return true;
                    }
                    return false;
                } catch (err) {
                    return false;
                }
            }

            const handleKeydown = (e) => {
                const activeTag = doc.activeElement.tagName;
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag)) {
                    if (doc.activeElement.type === 'text') {
                        return;
                    }
                }

                const key = e.key;

                if (key >= '1' && key <= '6') {
                    e.preventDefault();
                    e.stopPropagation();

                    if (isProcessing) return;
                    isProcessing = true;

                    const index = parseInt(key) - 1;
                    clickByText(`:::OPT_${index}:::`);
                    highlightOptionFeedback(index);

                    setTimeout(() => {
                        isProcessing = false;
                    }, 50);
                    return;
                }

                if (key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();

                    if (isProcessing) return;
                    isProcessing = true;

                    clickByText(":::NAV_ENTER:::");
                    highlightEnterFeedback();

                    setTimeout(() => {
                        isProcessing = false;
                    }, 100);
                    return;
                }

                if (key === 'ArrowLeft' || key === 'ArrowRight') {
                    e.preventDefault();
                    e.stopPropagation();

                    if (isProcessing) return;
                    isProcessing = true;

                    const keyword = key === 'ArrowLeft' ? ":::NAV_PREV:::" : ":::NAV_NEXT:::";
                    clickByText(keyword);
                    highlightArrowFeedback(key);

                    setTimeout(() => {
                        isProcessing = false;
                    }, 100);
                    return;
                }
            };

            function highlightOptionFeedback(index) {
                const mainSection = doc.querySelector('section[data-testid="stMain"]');
                if (!mainSection) return;

                const radios = mainSection.querySelectorAll('div[data-testid="stRadio"] label');
                if (radios && index < radios.length) {
                    const label = radios[index];
                    const originalBg = label.style.backgroundColor;
                    label.style.backgroundColor = '#e3f2fd';
                    label.style.transition = 'background-color 0.3s';

                    setTimeout(() => {
                        label.style.backgroundColor = originalBg || '';
                    }, 300);
                }

                const checkboxes = mainSection.querySelectorAll('div[data-testid="stCheckbox"] label');
                if (checkboxes && index < checkboxes.length) {
                    const label = checkboxes[index];
                    const originalBg = label.style.backgroundColor;
                    label.style.backgroundColor = '#e3f2fd';
                    label.style.transition = 'background-color 0.3s';

                    setTimeout(() => {
                        label.style.backgroundColor = originalBg || '';
                    }, 300);
                }

                showFloatingHint(`按键 ${index + 1}`);
            }

            function highlightEnterFeedback() {
                showFloatingHint('提交答案');

                const buttons = Array.from(doc.querySelectorAll('button'));
                const submitBtn = buttons.find(btn =>
                    btn.innerText && (btn.innerText.includes('提交') || btn.innerText.includes('下一题'))
                );
                if (submitBtn) {
                    const originalBg = submitBtn.style.backgroundColor;
                    submitBtn.style.backgroundColor = '#4CAF50';
                    submitBtn.style.color = 'white';

                    setTimeout(() => {
                        submitBtn.style.backgroundColor = originalBg || '';
                        submitBtn.style.color = '';
                    }, 300);
                }
            }

            function highlightArrowFeedback(key) {
                const direction = key === 'ArrowLeft' ? '上一题' : '下一题';
                showFloatingHint(direction);
            }

            function showFloatingHint(text) {
                const existingHint = doc.getElementById('keyboard-feedback-hint');
                if (existingHint) {
                    existingHint.remove();
                }

                const hint = doc.createElement('div');
                hint.id = 'keyboard-feedback-hint';
                hint.innerHTML = `
                    <div style="
                        position: fixed;
                        top: 100px;
                        right: 30px;
                        background: rgba(76, 175, 80, 0.9);
                        color: white;
                        padding: 10px 20px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        z-index: 99999;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                        backdrop-filter: blur(5px);
                        animation: fadeInOut 1s ease-in-out;
                        border: 1px solid rgba(255,255,255,0.2);
                    ">
                        🎮 ${text}
                    </div>
                `;

                const style = doc.createElement('style');
                style.textContent = `
                    @keyframes fadeInOut {
                        0% { opacity: 0; transform: translateY(-20px); }
                        20% { opacity: 1; transform: translateY(0); }
                        80% { opacity: 1; transform: translateY(0); }
                        100% { opacity: 0; transform: translateY(-20px); }
                    }
                `;

                doc.head.appendChild(style);
                doc.body.appendChild(hint);

                setTimeout(() => {
                    if (hint.parentNode) {
                        hint.parentNode.removeChild(hint);
                    }
                }, 1000);
            }

            function initKeyboard() {
                try {
                    doc.removeEventListener('keydown', handleKeydown);
                    doc.addEventListener('keydown', handleKeydown, { capture: true });

                    hidePhantomButtons();

                    if (!window.phantomObserver) {
                        window.phantomObserver = new MutationObserver(() => {
                            hidePhantomButtons();
                        });
                        window.phantomObserver.observe(doc.body, {
                            childList: true,
                            subtree: true,
                            attributes: true
                        });
                    }
                } catch (err) {
                    console.error('键盘控制初始化失败:', err);
                }
            }

            setTimeout(() => {
                initKeyboard();
            }, 1000);

            window.__cleanupPhantomKeyboard = function() {
                if (window.phantomObserver) {
                    window.phantomObserver.disconnect();
                    window.phantomObserver = null;
                }
                doc.removeEventListener('keydown', handleKeydown);
            };

        })();
        </script>
        """,
        height=0,
    )


def cleanup_keyboard_controls():
    """清理键盘控制"""
    components.html(
        """
        <script>
        if (window.__cleanupPhantomKeyboard) {
            window.__cleanupPhantomKeyboard();
        }
        const doc = window.parent.document;
        doc.removeEventListener('keydown', handleKeydown);
        </script>
        """,
        height=0
    )
