// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏警告消息
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.classList.add('fade');
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 3000);
    });
    
    // 图片点击放大
    var newsImages = document.querySelectorAll('.news-images img');
    newsImages.forEach(function(img) {
        img.addEventListener('click', function() {
            window.open(this.src, '_blank');
        });
    });
    
    // 高亮搜索关键词
    var keyword = document.getElementById('keyword');
    if (keyword && keyword.value) {
        var newsCards = document.querySelectorAll('.news-card');
        newsCards.forEach(function(card) {
            var title = card.querySelector('.card-title');
            if (title) {
                var text = title.innerText;
                if (text.includes(keyword.value)) {
                    var regex = new RegExp(keyword.value, 'gi');
                    title.innerHTML = text.replace(regex, '<mark>$&</mark>');
                }
            }
        });
    }
});