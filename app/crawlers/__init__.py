from app.crawlers.factory import CrawlerFactory

def run_crawlers(sources=None, days=1, max_news=100, async_mode=True, enhanced=False, **options):
    """运行爬虫的统一入口函数"""
    factory = CrawlerFactory()
    results = {}
    
    if not sources:
        # 如果没有指定源，使用所有可用的源
        sources = factory.get_supported_sources()
    elif isinstance(sources, str):
        # 如果是单个源，转换为列表
        sources = [sources]
    
    for source in sources:
        try:
            if enhanced:
                crawler = factory.create_enhanced_crawler(source, **options)
            else:
                crawler = factory.create_crawler(source, **options)
                
            if async_mode and hasattr(crawler, 'crawl_async'):
                import asyncio
                results[source] = asyncio.run(crawler.crawl_async(days=days, max_news=max_news))
            else:
                results[source] = crawler.crawl(days=days, max_news=max_news)
        except Exception as e:
            results[source] = {'error': str(e)}
    
    return results

# Make the function available when importing from app.crawlers
__all__ = ['run_crawlers']
