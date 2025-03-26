/**
 * 财经新闻爬虫系统 - 主JavaScript文件
 */

// 在DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
  // 移动端筛选条件折叠/展开
  initFilterToggle();
  
  // 添加加载状态
  initLoadingState();
  
  // 初始化工具提示
  initTooltips();
  
  // 初始化搜索框自动完成
  initSearchAutocomplete();
  
  // 初始化性能优化
  initLazyLoading();
  initOptimizedEvents();
  
  // 初始化动画
  initAnimations();
  
  // 初始化AJAX拦截器
  initAjaxInterceptor();
  
  // 初始化主题切换
  initThemeToggle();
  
  // 增强筛选条件反馈
  enhanceFilterFeedback();
});

/**
 * 初始化筛选条件折叠/展开功能
 */
function initFilterToggle() {
  const filterToggle = document.querySelector('.filter-toggle');
  if (filterToggle) {
    filterToggle.addEventListener('click', function() {
      const filterContent = document.querySelector('.filter-content');
      filterContent.classList.toggle('expanded');
      
      // 更新ARIA状态
      const expanded = filterContent.classList.contains('expanded');
      filterToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      
      // 更新图标
      const icon = filterToggle.querySelector('.icon-arrow-down, .icon-arrow-up');
      if (icon) {
        if (expanded) {
          icon.className = icon.className.replace('icon-arrow-down', 'icon-arrow-up');
        } else {
          icon.className = icon.className.replace('icon-arrow-up', 'icon-arrow-down');
        }
      }
    });
    
    // 在移动端默认展开筛选条件
    if (window.innerWidth > 768) {
      const filterContent = document.querySelector('.filter-content');
      filterContent.classList.add('expanded');
      filterToggle.setAttribute('aria-expanded', 'true');
    }
  }
}

/**
 * 增强筛选条件反馈
 */
function enhanceFilterFeedback() {
  const filterOptions = document.querySelectorAll('.filter-option');
  
  filterOptions.forEach(option => {
    option.addEventListener('click', function(e) {
      // 如果已经是激活状态，不需要额外反馈
      if (this.classList.contains('active')) {
        return;
      }
      
      // 添加选中反馈动画类
      this.classList.add('just-selected');
      
      // 动画结束后移除类
      setTimeout(() => {
        this.classList.remove('just-selected');
      }, 300);
      
      // 更新ARIA状态
      this.setAttribute('aria-pressed', 'true');
      
      // 获取同组的其他选项
      const parentGroup = this.closest('.filter-options');
      if (parentGroup) {
        const siblings = parentGroup.querySelectorAll('.filter-option:not(.just-selected)');
        siblings.forEach(sibling => {
          sibling.setAttribute('aria-pressed', 'false');
        });
      }
    });
  });
}

/**
 * 初始化加载状态
 */
function initLoadingState() {
  // 获取加载器元素
  const loader = document.getElementById('loader');
  
  // 如果没有加载文本，添加一个
  if (loader && !loader.querySelector('.loader-text')) {
    const loaderText = document.createElement('div');
    loaderText.className = 'loader-text';
    loaderText.textContent = '正在加载数据，请稍候...';
    loader.appendChild(loaderText);
  }
  
  // 为所有筛选链接添加加载效果
  const filterLinks = document.querySelectorAll('.filter-option, .pagination-link:not(.disabled)');
  filterLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      // 不阻止默认行为，让链接正常工作
      showGlobalLoadingState();
    });
  });
  
  // 为搜索按钮添加加载效果
  const searchForm = document.querySelector('form');
  if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
      showGlobalLoadingState();
    });
  }
  
  // 为视图切换按钮添加加载效果
  const viewOptions = document.querySelectorAll('.view-option');
  viewOptions.forEach(option => {
    option.addEventListener('click', function(e) {
      showGlobalLoadingState();
    });
  });
  
  // 页面加载完成后隐藏加载状态
  window.addEventListener('load', function() {
    hideGlobalLoadingState();
  });
}

/**
 * 显示全局加载状态
 */
function showGlobalLoadingState() {
  const loader = document.getElementById('loader');
  if (loader) {
    loader.classList.add('active');
    // 设置焦点陷阱
    document.body.setAttribute('aria-busy', 'true');
    // 通知屏幕阅读器
    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('aria-live', 'assertive');
    liveRegion.className = 'sr-only';
    liveRegion.textContent = '页面正在加载中，请稍候';
    document.body.appendChild(liveRegion);
    
    // 2秒后移除通知
    setTimeout(() => {
      if (document.body.contains(liveRegion)) {
        document.body.removeChild(liveRegion);
      }
    }, 2000);
  }
}

/**
 * 隐藏全局加载状态
 */
function hideGlobalLoadingState() {
  const loader = document.getElementById('loader');
  if (loader) {
    loader.classList.remove('active');
    document.body.setAttribute('aria-busy', 'false');
  }
}

/**
 * 显示加载状态（局部）
 */
function showLoadingState() {
  const newsList = document.querySelector('.news-list');
  if (!newsList) return;
  
  // 保存当前滚动位置
  const scrollPosition = window.scrollY;
  
  // 清空新闻列表并添加骨架屏
  newsList.innerHTML = '';
  for (let i = 0; i < 5; i++) {
    const skeletonItem = document.createElement('div');
    skeletonItem.className = 'news-card skeleton';
    skeletonItem.innerHTML = `
      <div class="skeleton-title"></div>
      <div class="skeleton-summary"></div>
      <div class="skeleton-meta"></div>
    `;
    newsList.appendChild(skeletonItem);
  }
  
  // 添加加载状态的ARIA属性
  newsList.setAttribute('aria-busy', 'true');
  
  // 滚动到顶部
  window.scrollTo(0, scrollPosition);
}

/**
 * 初始化工具提示
 */
function initTooltips() {
  const tooltipElements = document.querySelectorAll('[title]');
  tooltipElements.forEach(element => {
    element.addEventListener('mouseenter', function() {
      const title = this.getAttribute('title');
      this.removeAttribute('title');
      
      const tooltip = document.createElement('div');
      tooltip.className = 'tooltip';
      tooltip.textContent = title;
      document.body.appendChild(tooltip);
      
      const rect = this.getBoundingClientRect();
      tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
      tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
      
      this.addEventListener('mouseleave', function() {
        document.body.removeChild(tooltip);
        this.setAttribute('title', title);
      }, { once: true });
    });
  });
}

/**
 * 初始化搜索框自动完成
 */
function initSearchAutocomplete() {
  const searchInput = document.querySelector('.search-input');
  if (!searchInput) return;
  
  // 创建自动完成下拉框
  const autocompleteDropdown = document.createElement('div');
  autocompleteDropdown.className = 'autocomplete-dropdown';
  searchInput.parentNode.appendChild(autocompleteDropdown);
  
  // 添加加载指示器
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'autocomplete-loading';
  loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';
  loadingIndicator.style.display = 'none';
  searchInput.parentNode.appendChild(loadingIndicator);
  
  // 创建防抖函数
  const debouncedSearch = debounce(function(query) {
    if (query.length < 2) {
      autocompleteDropdown.innerHTML = '';
      autocompleteDropdown.style.display = 'none';
      return;
    }
    
    // 显示加载指示器
    loadingIndicator.style.display = 'block';
    
    // 模拟API请求延迟
    setTimeout(() => {
      // 模拟自动完成结果
      // 实际应用中，这里应该发送AJAX请求获取后端数据
      const mockResults = [
        '股票',
        '股市',
        '股价',
        '股东',
        '股份',
        '基金',
        '基金经理',
        '基金净值',
        '债券',
        '债市'
      ].filter(item => item.includes(query));
      
      // 隐藏加载指示器
      loadingIndicator.style.display = 'none';
      
      if (mockResults.length > 0) {
        // 使用DocumentFragment优化DOM操作
        const fragment = document.createDocumentFragment();
        
        mockResults.forEach(result => {
          const item = document.createElement('div');
          item.className = 'autocomplete-item';
          
          // 高亮匹配文本
          const highlightedText = result.replace(
            new RegExp(query, 'gi'),
            match => `<strong>${match}</strong>`
          );
          
          item.innerHTML = highlightedText;
          
          item.addEventListener('click', function() {
            searchInput.value = result;
            autocompleteDropdown.innerHTML = '';
            autocompleteDropdown.style.display = 'none';
            
            // 提交表单
            const form = searchInput.closest('form');
            if (form) form.submit();
          });
          
          fragment.appendChild(item);
        });
        
        autocompleteDropdown.innerHTML = '';
        autocompleteDropdown.appendChild(fragment);
        autocompleteDropdown.style.display = 'block';
      } else {
        autocompleteDropdown.innerHTML = '<div class="autocomplete-no-results">没有找到匹配结果</div>';
        autocompleteDropdown.style.display = 'block';
      }
    }, 300);
  }, 300);
  
  // 监听输入事件
  searchInput.addEventListener('input', function() {
    const query = this.value.trim();
    debouncedSearch(query);
  });
  
  // 键盘导航
  searchInput.addEventListener('keydown', function(e) {
    if (!autocompleteDropdown.style.display || autocompleteDropdown.style.display === 'none') {
      return;
    }
    
    const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
    const activeItem = autocompleteDropdown.querySelector('.autocomplete-item.active');
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (!activeItem) {
          items[0].classList.add('active');
        } else {
          const nextItem = activeItem.nextElementSibling;
          if (nextItem && nextItem.classList.contains('autocomplete-item')) {
            activeItem.classList.remove('active');
            nextItem.classList.add('active');
          }
        }
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        if (activeItem) {
          const prevItem = activeItem.previousElementSibling;
          if (prevItem && prevItem.classList.contains('autocomplete-item')) {
            activeItem.classList.remove('active');
            prevItem.classList.add('active');
          }
        }
        break;
        
      case 'Enter':
        if (activeItem) {
          e.preventDefault();
          activeItem.click();
        }
        break;
        
      case 'Escape':
        e.preventDefault();
        autocompleteDropdown.innerHTML = '';
        autocompleteDropdown.style.display = 'none';
        break;
    }
  });
  
  // 点击页面其他地方时隐藏下拉框
  document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !autocompleteDropdown.contains(e.target)) {
      autocompleteDropdown.innerHTML = '';
      autocompleteDropdown.style.display = 'none';
    }
  });
}

/**
 * 性能优化 - 懒加载
 */
function initLazyLoading() {
  if ('IntersectionObserver' in window) {
    const lazyLoadObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const newsCard = entry.target;
          newsCard.classList.add('visible');
          observer.unobserve(newsCard);
        }
      });
    });
    
    document.querySelectorAll('.news-card').forEach(card => {
      lazyLoadObserver.observe(card);
    });
  } else {
    // 降级处理
    document.querySelectorAll('.news-card').forEach(card => {
      card.classList.add('visible');
    });
  }
}

/**
 * 性能优化 - 事件优化
 */
function initOptimizedEvents() {
  // 使用事件委托优化点击事件
  document.addEventListener('click', function(e) {
    // 处理筛选选项点击
    if (e.target.classList.contains('filter-option') || e.target.closest('.filter-option')) {
      const filterOption = e.target.classList.contains('filter-option') ? e.target : e.target.closest('.filter-option');
      if (!filterOption.classList.contains('active')) {
        showLoadingState();
      }
    }
    
    // 处理分页链接点击
    if (e.target.classList.contains('pagination-link') || e.target.closest('.pagination-link:not(.disabled)')) {
      const paginationLink = e.target.classList.contains('pagination-link') ? e.target : e.target.closest('.pagination-link');
      if (!paginationLink.classList.contains('disabled')) {
        showLoadingState();
      }
    }
  });
  
  // 使用防抖函数优化搜索
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    const originalHandler = searchInput._inputHandler;
    if (originalHandler) {
      searchInput.removeEventListener('input', originalHandler);
      
      // 添加防抖处理
      const debouncedHandler = debounce(function(e) {
        originalHandler.call(this, e);
      }, 300);
      
      searchInput.addEventListener('input', debouncedHandler);
      searchInput._inputHandler = debouncedHandler;
    }
  }
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

/**
 * 初始化动画效果
 */
function initAnimations() {
  if (!('IntersectionObserver' in window)) {
    // 如果浏览器不支持IntersectionObserver，直接显示所有卡片
    document.querySelectorAll('.news-card').forEach(card => {
      card.classList.add('visible');
    });
    return;
  }
  
  // 新闻卡片淡入动画
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // 一旦显示，停止观察
        observer.unobserve(entry.target);
      }
    });
  }, {
    root: null,
    threshold: 0.1,
    rootMargin: '0px'
  });

  // 观察所有新闻卡片
  document.querySelectorAll('.news-card').forEach(card => {
    observer.observe(card);
  });
}

/**
 * 加载状态指示器控制
 */
const loader = {
  element: document.getElementById('loader'),
  show: function() {
    if (this.element) {
      this.element.classList.add('active');
    }
  },
  hide: function() {
    if (this.element) {
      this.element.classList.remove('active');
    }
  }
};

/**
 * 初始化AJAX请求拦截器
 */
function initAjaxInterceptor() {
  // 保存原始的fetch方法
  const originalFetch = window.fetch;
  
  // 重写fetch方法
  window.fetch = function() {
    loader.show();
    
    return originalFetch.apply(this, arguments)
      .then(response => {
        loader.hide();
        return response;
      })
      .catch(error => {
        loader.hide();
        throw error;
      });
  };
  
  // 监听所有表单提交
  document.addEventListener('submit', function(e) {
    if (e.target.tagName === 'FORM') {
      loader.show();
    }
  });
}

/**
 * 主题切换功能
 */
function initThemeToggle() {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;
  
  const themeIcon = themeToggle.querySelector('i');
  if (!themeIcon) return;
  
  // 检查本地存储中的主题设置
  const currentTheme = localStorage.getItem('theme') || 'light';
  
  // 应用保存的主题
  if (currentTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeIcon.classList.remove('fa-moon');
    themeIcon.classList.add('fa-sun');
  }
  
  // 切换主题
  themeToggle.addEventListener('click', function() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // 更新主题
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // 更新图标
    if (newTheme === 'dark') {
      themeIcon.classList.remove('fa-moon');
      themeIcon.classList.add('fa-sun');
    } else {
      themeIcon.classList.remove('fa-sun');
      themeIcon.classList.add('fa-moon');
    }
    
    // 保存设置到本地存储
    localStorage.setItem('theme', newTheme);
    
    // 触发自定义事件，通知图表等组件更新颜色
    document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
  });
  
  // 添加键盘支持
  themeToggle.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      themeToggle.click();
    }
  });
} 