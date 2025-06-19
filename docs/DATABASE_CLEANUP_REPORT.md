# 数据库文件整理报告

整理时间: 2025-05-31 17:09:40

## 新的数据库目录结构

```
databases/
├── sina_finance.db          # 新浪财经数据库
├── eastmoney_finance.db     # 东方财富数据库
├── netease_finance.db       # 网易财经数据库
├── ifeng_finance.db         # 凤凰财经数据库
├── backups/                 # 备份文件
├── archives/                # 归档文件
└── temp/                    # 临时文件
```

## 移动的文件

- D:\Git\Github\NewsLook\data\eastmoney.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\finance_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\netease.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\data\news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\test_optimized.db -> D:\Git\Github\NewsLook\databases\archives\test_optimized.db
- D:\Git\Github\NewsLook\data\test_sina_perf.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\data\东方财富.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\新浪财经.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\data\网易财经.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\data\�����Ƹ�.db -> D:\Git\Github\NewsLook\databases\archives\�����Ƹ�.db
- D:\Git\Github\NewsLook\data\db\finance_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\db\user_preferences.db -> D:\Git\Github\NewsLook\databases\archives\user_preferences.db
- D:\Git\Github\NewsLook\data\db\东方财富.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\db\凤凰财经.db -> D:\Git\Github\NewsLook\databases\ifeng_finance.db
- D:\Git\Github\NewsLook\data\db\新浪财经.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\data\db\网易财经.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\data\db\�����Ƹ�.db -> D:\Git\Github\NewsLook\databases\archives\�����Ƹ�_20250531_170940.db
- D:\Git\Github\NewsLook\data\sources\东方财富.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\sources\新浪财经.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\data\sources\网易财经.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\data\sources\���ײƾ�.db -> D:\Git\Github\NewsLook\databases\archives\���ײƾ�.db
- D:\Git\Github\NewsLook\data\db\data\test_db.db -> D:\Git\Github\NewsLook\databases\archives\test_db.db
- D:\Git\Github\NewsLook\data\db\data\test_single.db -> D:\Git\Github\NewsLook\databases\archives\test_single.db
- D:\Git\Github\NewsLook\data\db\data\东方财富.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\data\db\data\�����Ƹ�.db -> D:\Git\Github\NewsLook\databases\archives\�����Ƹ�_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\sources\网易财经.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\data\db\data\db\新浪财经.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\eastmoney.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\ifeng.db -> D:\Git\Github\NewsLook\databases\ifeng_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\netease.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\sina.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\sources\东方财富.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\sources\凤凰财经.db -> D:\Git\Github\NewsLook\databases\ifeng_finance.db
- D:\Git\Github\NewsLook\test_crawl\data\sources\新浪财经.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\db\finance_news.db -> D:\Git\Github\NewsLook\databases\archives\finance_news.db
- D:\Git\Github\NewsLook\test.db -> D:\Git\Github\NewsLook\databases\archives\test.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\data\finance_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\data\news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\eastmoney_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\finance_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\test_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\东方财富_news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\新浪财经_news.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\未知来源_news.db -> D:\Git\Github\NewsLook\databases\archives\未知来源_news.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\网易财经_news.db -> D:\Git\Github\NewsLook\databases\netease_finance.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\db\腾讯财经_news.db -> D:\Git\Github\NewsLook\databases\archives\腾讯财经_news.db
- D:\Git\Github\NewsLook\_archived_today3_20250324200011\data\db\news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\test_data\db\eastmoney_test.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\test_data\db\sina_test.db -> D:\Git\Github\NewsLook\databases\sina_finance.db
- D:\Git\Github\NewsLook\tests\data\test_finance.db -> D:\Git\Github\NewsLook\databases\archives\test_finance.db
- D:\Git\Github\NewsLook\scripts\data\news.db -> D:\Git\Github\NewsLook\databases\eastmoney_finance.db
- D:\Git\Github\NewsLook\path\to\your\database.db -> D:\Git\Github\NewsLook\databases\archives\database.db
- D:\Git\Github\NewsLook\newslook\crawlers\data\db\finance_news.db -> D:\Git\Github\NewsLook\databases\archives\finance_news_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\database.db -> D:\Git\Github\NewsLook\databases\archives\database_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\finance_news_20250531_170940.db -> D:\Git\Github\NewsLook\databases\archives\finance_news_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\test.db -> D:\Git\Github\NewsLook\databases\archives\test_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\test_db.db -> D:\Git\Github\NewsLook\databases\archives\test_db_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\test_finance.db -> D:\Git\Github\NewsLook\databases\archives\test_finance_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\test_optimized.db -> D:\Git\Github\NewsLook\databases\archives\test_optimized_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\test_single.db -> D:\Git\Github\NewsLook\databases\archives\test_single_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\user_preferences.db -> D:\Git\Github\NewsLook\databases\archives\user_preferences_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\未知来源_news.db -> D:\Git\Github\NewsLook\databases\archives\未知来源_news_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\腾讯财经_news.db -> D:\Git\Github\NewsLook\databases\archives\腾讯财经_news_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\���ײƾ�.db -> D:\Git\Github\NewsLook\databases\archives\���ײƾ�_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\�����Ƹ�.db -> D:\Git\Github\NewsLook\databases\archives\�����Ƹ�_20250531_170940.db
- D:\Git\Github\NewsLook\databases\archives\�����Ƹ�_20250531_170940.db -> D:\Git\Github\NewsLook\databases\archives\�����Ƹ�_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\app\data\news.db -> D:\Git\Github\NewsLook\databases\archives\news.db
- D:\Git\Github\NewsLook\app\data\performance.db -> D:\Git\Github\NewsLook\databases\archives\performance.db

## 备份的文件

- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\eastmoney_20250322_210147.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_20250322_210147_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_172140.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172140_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_172543.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172543_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_172823.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172823_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_172936.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172936_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_173005.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173005_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_173405.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173405_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_173623.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173623_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_173655.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173655_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_173736.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173736_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_174150.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174150_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_174517.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174517_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_174657.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174657_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_174911.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174911_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_175112.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175112_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_175149.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175149_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_175251.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175251_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_175847.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175847_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_180006.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_180006_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_201740.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_201740_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_202705.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202705_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\new_news_20250322_202934.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202934_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\tencent_finance_20250322_203541.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_203541_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\tencent_finance_20250322_205148.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205148_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\tencent_finance_20250322_205714.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205714_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\tencent_finance_20250322_210620.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_210620_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\东方财富网_backup_20250323171833.db -> D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323171833_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\东方财富网_backup_20250323172317.db -> D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323172317_20250531_170940.db
- D:\Git\Github\NewsLook\data\db\backup\未知来源_backup_20250323164558.db -> D:\Git\Github\NewsLook\databases\backups\未知来源_backup_20250323164558_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\ifeng_finance.db -> D:\Git\Github\NewsLook\databases\backups\ifeng_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\ifeng_finance.db -> D:\Git\Github\NewsLook\databases\backups\ifeng_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\netease_finance.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\sina_finance.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\eastmoney_finance.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\eastmoney_20250322_210147_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_20250322_210147_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\eastmoney_finance_backup_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\ifeng_finance_backup_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\ifeng_finance_backup_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\netease_finance_backup_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172140_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172140_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172543_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172543_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172823_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172823_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172936_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_172936_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173005_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173005_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173405_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173405_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173623_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173623_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173655_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173655_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173736_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_173736_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174150_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174150_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174517_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174517_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174657_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174657_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174911_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_174911_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175112_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175112_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175149_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175149_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175251_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175251_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175847_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_175847_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_180006_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_180006_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_201740_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_201740_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202705_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202705_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202934_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\new_news_20250322_202934_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\sina_finance_backup_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_203541_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_203541_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205148_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205148_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205714_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_205714_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_210620_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\tencent_finance_20250322_210620_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323171833_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323171833_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323172317_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\东方财富网_backup_20250323172317_20250531_170940_20250531_170940.db
- D:\Git\Github\NewsLook\databases\backups\未知来源_backup_20250323164558_20250531_170940.db -> D:\Git\Github\NewsLook\databases\backups\未知来源_backup_20250323164558_20250531_170940_20250531_170940.db

## 错误信息

- 移动到归档目录失败 D:\Git\Github\NewsLook\databases\archives\finance_news.db: [WinError 183] 当文件已存在时，无法创建该文件。: 'D:\\Git\\Github\\NewsLook\\databases\\archives\\finance_news_20250531_170940.db'

## 数据库文件统计

| 数据源 | 标准文件名 | 状态 |
|--------|------------|------|
| sina | sina_finance.db | ✅ 存在 |
| eastmoney | eastmoney_finance.db | ✅ 存在 |
| netease | netease_finance.db | ✅ 存在 |
| ifeng | ifeng_finance.db | ✅ 存在 |
