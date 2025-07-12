/*!
 * NewsLook 财经新闻爬虫系统 - 主JavaScript文件
 * 处理页面交互、编码修复、用户体验优化
 */

(function() {
    'use strict';
    
    // ===== 全局配置 =====
    const NewsLook = {
        config: {
            debug: false,
            apiBaseUrl: '/api',
            animationDuration: 300,
            toastDuration: 3000
        },
        
        // 工具函数
        utils: {},
        
        // 页面模块
        modules: {}
    };
    
    // ===== 工具函数 =====
    NewsLook.utils = {
        /**
         * 检测文本是否包含编码问题
         * @param {string} text - 待检测的文本
         * @returns {boolean}
         */
        containsEncodingIssues: function(text) {
            if (!text || typeof text !== 'string') return false;
            
            // 检测常见的编码问题
            const patterns = [
                /\\u[\da-f]{4}/gi,           // Unicode转义序列
                /&#\d+;/g,                   // HTML实体编码
                /&[a-z]+;/gi,               // HTML命名实体
                /[\u00c0-\u00ff]{2,}/g,     // 双字节编码问题
                /\?{2,}/g,                  // 多个问号（乱码）
                /\ufffd/g                   // 替换字符
            ];
            
            return patterns.some(pattern => pattern.test(text));
        },
        
        /**
         * 修复编码问题
         * @param {string} text - 待修复的文本
         * @returns {string}
         */
        fixEncodingIssues: function(text) {
            if (!text || typeof text !== 'string') return text;
            
            try {
                // 修复Unicode转义序列
                if (text.includes('\\u')) {
                    text = text.replace(/\\u([\da-f]{4})/gi, function(match, code) {
                        return String.fromCharCode(parseInt(code, 16));
                    });
                }
                
                // 修复HTML实体编码
                const entityMap = {
                    '&amp;': '&',
                    '&lt;': '<',
                    '&gt;': '>',
                    '&quot;': '"',
                    '&#39;': "'",
                    '&nbsp;': ' '
                };
                
                Object.keys(entityMap).forEach(entity => {
                    text = text.replace(new RegExp(entity, 'g'), entityMap[entity]);
                });
                
                // 修复数字实体编码
                text = text.replace(/&#(\d+);/g, function(match, code) {
                    return String.fromCharCode(parseInt(code, 10));
                });
                
                return text;
            } catch (error) {
                console.warn('编码修复失败:', error);
                return text;
            }
        },
        
        /**
         * 从URL推断新闻来源
         * @param {string} url - 新闻URL
         * @returns {string}
         */
        inferSourceFromUrl: function(url) {
            if (!url) return '未知来源';
            
            const sourceMap = {
                'eastmoney.com': '东方财富网',
                'sina.com': '新浪财经',
                'sina.cn': '新浪财经',
                'finance.sina': '新浪财经',
                'qq.com': '腾讯财经',
                'finance.qq': '腾讯财经',
                '163.com': '网易财经',
                'money.163': '网易财经',
                'ifeng.com': '凤凰财经',
                'jrj.com': '金融界',
                'cnstock.com': '中国证券网',
                'hexun.com': '和讯网',
                'cs.com.cn': '中证网',
                'xinhuanet.com': '新华网',
                'people.com.cn': '人民网',
                'cctv.com': 'CCTV',
                'stcn.com': '证券时报网',
                '21jingji.com': '21世纪经济报道',
                'chinanews.com': '中新网',
                'cnfol.com': '中金在线',
                'caixin.com': '财新网'
            };
            
            const urlLower = url.toLowerCase();
            for (const domain in sourceMap) {
                if (urlLower.includes(domain)) {
                    return sourceMap[domain];
                }
            }
            
            // 提取主域名
            try {
                const urlObj = new URL(url);
                const hostname = urlObj.hostname;
                const parts = hostname.split('.');
                if (parts.length >= 2) {
                    return parts[parts.length - 2] + '.' + parts[parts.length - 1];
                }
                return hostname;
            } catch (error) {
                return '未知来源';
            }
        },
        
        /**
         * 格式化时间
         * @param {string} timeStr - 时间字符串
         * @returns {string}
         */
        formatTime: function(timeStr) {
            try {
                const date = new Date(timeStr);
                const now = new Date();
                const diff = now - date;
                
                const minute = 60 * 1000;
                const hour = 60 * minute;
                const day = 24 * hour;
                
                if (diff < minute) {
                    return '刚刚';
                } else if (diff < hour) {
                    return Math.floor(diff / minute) + '分钟前';
                } else if (diff < day) {
                    return Math.floor(diff / hour) + '小时前';
                } else if (diff < 7 * day) {
                    return Math.floor(diff / day) + '天前';
                } else {
                    return date.toLocaleDateString('zh-CN');
                }
            } catch (error) {
                return timeStr;
            }
        },
        
        /**
         * 显示通知消息
         * @param {string} message - 消息内容
         * @param {string} type - 消息类型 (success, error, info, warning)
         */
        showToast: function(message, type = 'info') {
            // 移除现有的toast
            const existingToast = document.querySelector('.toast-message');
            if (existingToast) {
                existingToast.remove();
            }
            
            // 创建toast元素
            const toast = document.createElement('div');
            toast.className = `toast-message alert alert-${type}`;
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                min-width: 300px;
                animation: slideInRight 0.3s ease-out;
            `;
            toast.textContent = message;
            
            // 添加关闭按钮
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '&times;';
            closeBtn.className = 'btn-close';
            closeBtn.style.cssText = `
                background: none;
                border: none;
                font-size: 1.5rem;
                line-height: 1;
                opacity: 0.5;
                float: right;
                margin-left: 10px;
                cursor: pointer;
            `;
            closeBtn.onclick = () => toast.remove();
            toast.appendChild(closeBtn);
            
            document.body.appendChild(toast);
            
            // 自动移除
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.animation = 'slideOutRight 0.3s ease-in';
                    setTimeout(() => toast.remove(), 300);
                }
            }, NewsLook.config.toastDuration);
        },
        
        /**
         * 防抖函数
         * @param {Function} func - 要防抖的函数
         * @param {number} wait - 延迟时间
         * @returns {Function}
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };
    
    // ===== 编码修复模块 =====
    NewsLook.modules.encodingFixer = {
        init: function() {
            this.fixPageContent();
            this.observeContentChanges();
        },
        
        fixPageContent: function() {
            // 修复新闻标题
            document.querySelectorAll('.news-title a, .card-title a').forEach(element => {
                const text = element.textContent;
                if (NewsLook.utils.containsEncodingIssues(text)) {
                    const fixed = NewsLook.utils.fixEncodingIssues(text);
                    if (fixed && fixed !== text) {
                        element.textContent = fixed;
                        if (NewsLook.config.debug) {
                            console.log('修复标题编码:', text, '->', fixed);
                        }
                    }
                }
            });
            
            // 修复新闻来源
            document.querySelectorAll('.badge-source, .badge.bg-primary').forEach(element => {
                const text = element.textContent.trim();
                if (text === '未知来源' || NewsLook.utils.containsEncodingIssues(text)) {
                    // 尝试从链接推断来源
                    const newsCard = element.closest('.card, .news-item');
                    if (newsCard) {
                        const linkElement = newsCard.querySelector('a[href]');
                        if (linkElement) {
                            const href = linkElement.getAttribute('href');
                            if (href) {
                                const inferredSource = NewsLook.utils.inferSourceFromUrl(href);
                                if (inferredSource !== '未知来源') {
                                    element.textContent = inferredSource;
                                    element.classList.add('source-inferred');
                                }
                            }
                        }
                    }
                }
            });
            
            // 修复其他文本内容
            document.querySelectorAll('.news-content, .card-text').forEach(element => {
                const text = element.textContent;
                if (NewsLook.utils.containsEncodingIssues(text)) {
                    const fixed = NewsLook.utils.fixEncodingIssues(text);
                    if (fixed && fixed !== text) {
                        element.textContent = fixed;
                    }
                }
            });
        },
        
        observeContentChanges: function() {
            // 监听动态内容变化
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // 延迟处理，确保内容完全加载
                                setTimeout(() => {
                                    this.fixNodeContent(node);
                                }, 100);
                            }
                        });
                    }
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        },
        
        fixNodeContent: function(node) {
            // 修复新增节点的编码问题
            const textElements = node.querySelectorAll('.news-title, .news-content, .badge-source');
            textElements.forEach(element => {
                const text = element.textContent;
                if (NewsLook.utils.containsEncodingIssues(text)) {
                    const fixed = NewsLook.utils.fixEncodingIssues(text);
                    if (fixed && fixed !== text) {
                        element.textContent = fixed;
                    }
                }
            });
        }
    };
    
    // ===== 分页模块 =====
    NewsLook.modules.pagination = {
        init: function() {
            this.addKeyboardSupport();
            this.addSmoothScrolling();
        },
        
        addKeyboardSupport: function() {
            document.addEventListener('keydown', (e) => {
                // 只在没有焦点在输入框时响应
                if (document.activeElement.tagName === 'INPUT' || 
                    document.activeElement.tagName === 'TEXTAREA') {
                    return;
                }
                
                const pagination = document.querySelector('.pagination');
                if (!pagination) return;
                
                let targetLink = null;
                
                switch(e.key) {
                    case 'ArrowLeft':
                    case 'p':
                        // 上一页
                        targetLink = pagination.querySelector('[aria-label="Previous"]:not(.disabled)');
                        break;
                    case 'ArrowRight':
                    case 'n':
                        // 下一页
                        targetLink = pagination.querySelector('[aria-label="Next"]:not(.disabled)');
                        break;
                    case 'Home':
                        // 第一页
                        targetLink = pagination.querySelector('.page-link[href*="page=1"]');
                        break;
                    case 'End':
                        // 最后一页
                        const lastPageLink = Array.from(pagination.querySelectorAll('.page-link'))
                            .filter(link => /page=\d+/.test(link.href))
                            .pop();
                        targetLink = lastPageLink;
                        break;
                }
                
                if (targetLink && !targetLink.closest('.disabled')) {
                    e.preventDefault();
                    targetLink.click();
                }
            });
        },
        
        addSmoothScrolling: function() {
            // 为分页链接添加平滑滚动
            document.querySelectorAll('.pagination .page-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    // 滚动到页面顶部
                    setTimeout(() => {
                        window.scrollTo({
                            top: 0,
                            behavior: 'smooth'
                        });
                    }, 100);
                });
            });
        }
    };
    
    // ===== 用户体验优化模块 =====
    NewsLook.modules.ux = {
        init: function() {
            this.addLoadingStates();
            this.addHoverEffects();
            this.addTimeFormatting();
            this.addSearchEnhancements();
        },
        
        addLoadingStates: function() {
            // 为表单提交添加加载状态
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function() {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        const originalText = submitBtn.textContent;
                        submitBtn.innerHTML = '<span class="spinner"></span> 搜索中...';
                        submitBtn.disabled = true;
                        
                        // 恢复按钮状态（防止页面不刷新的情况）
                        setTimeout(() => {
                            submitBtn.textContent = originalText;
                            submitBtn.disabled = false;
                        }, 5000);
                    }
                });
            });
        },
        
        addHoverEffects: function() {
            // 为卡片添加交互效果
            document.querySelectorAll('.card').forEach(card => {
                card.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                });
                
                card.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });
            
            // 为新闻项添加点击效果
            document.querySelectorAll('.news-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    // 如果点击的不是链接，则导航到新闻详情
                    if (e.target.tagName !== 'A' && !e.target.closest('a')) {
                        const titleLink = item.querySelector('.news-title a');
                        if (titleLink) {
                            titleLink.click();
                        }
                    }
                });
                
                // 添加鼠标样式
                item.style.cursor = 'pointer';
            });
        },
        
        addTimeFormatting: function() {
            // 格式化时间显示
            document.querySelectorAll('.news-meta').forEach(meta => {
                const timeText = meta.textContent;
                const timeMatch = timeText.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
                if (timeMatch) {
                    const formattedTime = NewsLook.utils.formatTime(timeMatch[1]);
                    meta.innerHTML = meta.innerHTML.replace(timeMatch[1], formattedTime);
                }
            });
        },
        
        addSearchEnhancements: function() {
            // 搜索框自动完成和建议
            const searchInput = document.querySelector('input[name="keyword"]');
            if (searchInput) {
                // 添加搜索历史支持
                const searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
                
                searchInput.addEventListener('focus', function() {
                    // 可以在这里添加搜索建议下拉框
                });
                
                // 保存搜索历史
                const searchForm = searchInput.closest('form');
                if (searchForm) {
                    searchForm.addEventListener('submit', function() {
                        const keyword = searchInput.value.trim();
                        if (keyword) {
                            // 更新搜索历史
                            const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
                            if (!history.includes(keyword)) {
                                history.unshift(keyword);
                                history.splice(10); // 只保留最近10个
                                localStorage.setItem('searchHistory', JSON.stringify(history));
                            }
                        }
                    });
                }
                
                // 添加清除按钮
                if (searchInput.value) {
                    this.addClearButton(searchInput);
                }
                
                searchInput.addEventListener('input', NewsLook.utils.debounce(() => {
                    if (searchInput.value) {
                        this.addClearButton(searchInput);
                    } else {
                        this.removeClearButton(searchInput);
                    }
                }, 300));
            }
        },
        
        addClearButton: function(input) {
            if (input.nextElementSibling && input.nextElementSibling.classList.contains('clear-btn')) {
                return; // 已存在
            }
            
            const clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'clear-btn';
            clearBtn.innerHTML = '&times;';
            clearBtn.style.cssText = `
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #999;
                z-index: 10;
            `;
            
            clearBtn.addEventListener('click', () => {
                input.value = '';
                input.focus();
                this.removeClearButton(input);
            });
            
            // 设置输入框容器为相对定位
            const container = input.parentNode;
            if (getComputedStyle(container).position === 'static') {
                container.style.position = 'relative';
            }
            
            container.appendChild(clearBtn);
        },
        
        removeClearButton: function(input) {
            const clearBtn = input.nextElementSibling;
            if (clearBtn && clearBtn.classList.contains('clear-btn')) {
                clearBtn.remove();
            }
        }
    };
    
    // ===== 错误处理模块 =====
    NewsLook.modules.errorHandler = {
        init: function() {
            this.handleImageErrors();
            this.handleLinkErrors();
            window.addEventListener('error', this.handleGlobalErrors.bind(this));
        },
        
        handleImageErrors: function() {
            document.querySelectorAll('img').forEach(img => {
                img.addEventListener('error', function() {
                    // 使用占位图片或隐藏图片
                    this.style.display = 'none';
                    
                    // 或者使用默认图片
                    // this.src = '/static/images/placeholder.png';
                });
            });
        },
        
        handleLinkErrors: function() {
            document.querySelectorAll('a[href]').forEach(link => {
                link.addEventListener('click', function(e) {
                    // 检查链接是否有效
                    const href = this.getAttribute('href');
                    if (!href || href === '#' || href === 'javascript:void(0)') {
                        e.preventDefault();
                        NewsLook.utils.showToast('链接暂时不可用', 'warning');
                    }
                });
            });
        },
        
        handleGlobalErrors: function(event) {
            if (NewsLook.config.debug) {
                console.error('页面错误:', event.error);
            }
            
            // 不向用户显示技术错误，只记录日志
            if (window.console && typeof window.console.error === 'function') {
                console.error('NewsLook Error:', event.error);
            }
        }
    };
    
    // ===== 初始化 =====
    document.addEventListener('DOMContentLoaded', function() {
        // 初始化所有模块
        try {
            NewsLook.modules.encodingFixer.init();
            NewsLook.modules.pagination.init();
            NewsLook.modules.ux.init();
            NewsLook.modules.errorHandler.init();
            
            if (NewsLook.config.debug) {
                console.log('NewsLook 初始化完成');
            }
            
            // 显示加载完成提示
            setTimeout(() => {
                document.body.classList.add('loaded');
            }, 100);
            
        } catch (error) {
            console.error('NewsLook 初始化失败:', error);
        }
    });
    
    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .loaded {
            animation: fadeIn 0.5s ease-out;
        }
    `;
    document.head.appendChild(style);
    
    // 暴露到全局作用域（仅用于调试）
    if (NewsLook.config.debug) {
        window.NewsLook = NewsLook;
    }
    
})(); 