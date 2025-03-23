#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图像识别模块 - 用于检测新闻中的广告图片

依赖项：
1. Pillow (PIL) - 图像处理基础库 [必需]
   pip install Pillow>=9.2.0

2. NumPy - 科学计算库 [必需]
   pip install numpy>=1.23.3

3. OpenCV (可选) - 高级图像处理和分析
   pip install opencv-python>=4.6.0

4. TensorFlow (可选) - 深度学习图像识别
   pip install tensorflow>=2.10.0
   
   注意：如果安装TensorFlow失败，可以尝试以下命令安装CPU版本:
   pip install tensorflow-cpu>=2.10.0
   
   或安装较低版本:
   pip install tensorflow==2.9.0

使用方法：
```python
from app.utils.image_detector import ImageDetector

# 初始化检测器（可选择指定缓存目录）
detector = ImageDetector(cache_dir='./image_cache')

# 重置广告计数
detector.reset_ad_count()

# 检查图像是否为广告
is_ad = detector.is_ad_image("https://example.com/image.jpg")

# 获取检测到的广告数量
ad_count = detector.get_ad_count()

# 在爬虫中的使用示例
# 在HTML内容中检测和过滤广告图片
image_content_soup = BeautifulSoup(content_html, 'html.parser')
for img in image_content_soup.find_all('img'):
    img_url = img.get('src')
    if img_url and detector.is_ad_image(img_url):
        # 从HTML中移除广告图片
        img.decompose()
```

特性：
1. 图像特征分析 - 通过分析颜色、边缘密度等特征识别广告
2. 感知哈希匹配 - 对比已知广告图片的哈希值快速识别
3. 深度学习模型支持 - 可选集成TensorFlow模型提高识别准确率
4. 广告图片缓存 - 避免重复处理相同图片提高性能
"""

import os
import logging
import base64
from io import BytesIO
import hashlib
import requests
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV (cv2) 未安装，部分高级图像识别功能将不可用。可通过 'pip install opencv-python>=4.6.0' 安装。")

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.warning("TensorFlow 未安装，深度学习图像识别功能将不可用。"
                  "如需使用深度学习功能，请尝试以下命令安装:\n"
                  "1. pip install tensorflow>=2.10.0\n"
                  "2. pip install tensorflow-cpu>=2.10.0 (仅CPU版本)\n"
                  "3. pip install tensorflow==2.9.0 (较低版本)")

logger = logging.getLogger(__name__)

class ImageDetector:
    """图像识别类，用于检测新闻中的广告图片"""
    
    # 广告图片的典型特征
    AD_IMAGE_FEATURES = {
        'logo_positions': ['bottom-right', 'top-right', 'bottom-left'],  # 品牌标志通常出现的位置
        'text_density': 'high',  # 广告图片通常文字密度较高
        'color_saturation': 'high',  # 广告图片通常色彩饱和度较高
        'aspect_ratios': [(16, 9), (4, 3), (1, 1), (2, 1)],  # 常见广告图片宽高比
    }
    
    # 已知广告图片的哈希值
    KNOWN_AD_IMAGE_HASHES = [
        # 这里可以存储已知广告图片的哈希值，用于快速匹配
    ]
    
    # 广告图片中常见的文本模式
    AD_TEXT_PATTERNS = [
        '点击', '下载', '安装', '立即', '优惠', '折扣', 
        '限时', '抢购', '特价', '活动', '促销', '会员'
    ]
    
    def __init__(self, cache_dir=None):
        """
        初始化图像识别器
        
        Args:
            cache_dir: 图片缓存目录，用于存储已处理过的图片信息
        """
        self.cache_dir = cache_dir
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        self.ad_count = 0  # 检测到的广告图片计数
        self.model = None  # 初始化模型为None
        
        # 如果TensorFlow可用，尝试加载预训练模型
        if TF_AVAILABLE:
            try:
                self._load_model()
                if self.model:
                    logger.info("深度学习模型加载成功")
            except Exception as e:
                logger.error(f"加载图像识别模型失败: {e}")
                self.model = None
    
    def _load_model(self):
        """加载预训练的图像识别模型"""
        # 这里是加载模型的代码，实际项目中需要替换为真实的模型路径
        model_path = os.environ.get('AD_MODEL_PATH')
        if model_path and os.path.exists(model_path):
            try:
                self.model = tf.keras.models.load_model(model_path)
                return True
            except Exception as e:
                logger.error(f"无法加载模型 {model_path}: {e}")
        else:
            logger.warning("未指定模型路径或模型文件不存在")
        return False
    
    def reset_ad_count(self):
        """重置广告计数"""
        self.ad_count = 0
    
    def get_ad_count(self):
        """获取当前检测到的广告数量"""
        return self.ad_count
    
    def compute_image_hash(self, image):
        """
        计算图像的感知哈希值
        
        Args:
            image: PIL Image对象或图像URL
            
        Returns:
            图像的感知哈希值
        """
        if isinstance(image, str):
            # 如果是URL，先下载图片
            try:
                response = requests.get(image, timeout=10)
                img = Image.open(BytesIO(response.content))
            except Exception as e:
                logger.error(f"下载图片失败: {image}, 错误: {e}")
                return None
        else:
            img = image
        
        # 转换为灰度图
        img = img.convert('L')
        # 缩小图片尺寸为8x8
        img = img.resize((8, 8), Image.LANCZOS)
        # 获取像素数据
        pixels = list(img.getdata())
        # 计算平均值
        avg = sum(pixels) / len(pixels)
        # 根据平均值生成哈希值
        hash_value = ''.join('1' if pixel >= avg else '0' for pixel in pixels)
        
        return hash_value
    
    def hamming_distance(self, hash1, hash2):
        """
        计算两个哈希值之间的汉明距离
        
        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值
            
        Returns:
            两个哈希值之间的汉明距离
        """
        return sum(ch1 != ch2 for ch1, ch2 in zip(hash1, hash2))
    
    def is_similar_to_known_ad(self, image_hash, threshold=5):
        """
        检查图像是否与已知广告图片相似
        
        Args:
            image_hash: 图像哈希值
            threshold: 相似度阈值，汉明距离小于此值则认为相似
            
        Returns:
            是否与已知广告图片相似
        """
        if not image_hash:
            return False
        
        # 如果没有已知的广告图片哈希，直接返回False
        if not self.KNOWN_AD_IMAGE_HASHES:
            return False
            
        for known_hash in self.KNOWN_AD_IMAGE_HASHES:
            if self.hamming_distance(image_hash, known_hash) < threshold:
                return True
        
        return False
    
    def analyze_image_features(self, image):
        """
        分析图像特征，判断是否具有广告特征
        
        Args:
            image: PIL Image对象
            
        Returns:
            是否具有广告特征，以及特征分析结果
        """
        features = {}
        
        # 分析图像尺寸比例
        width, height = image.size
        aspect_ratio = (width, height)
        features['aspect_ratio'] = aspect_ratio
        
        # 分析颜色饱和度
        enhancer = ImageEnhance.Color(image)
        color_variance = self._calculate_color_variance(image)
        features['color_variance'] = color_variance
        
        # 分析边缘特征（广告图片通常边缘较多）
        edge_density = self._calculate_edge_density(image)
        features['edge_density'] = edge_density
        
        # 综合分析结果
        ad_score = 0
        
        # 检查宽高比
        for ratio in self.AD_IMAGE_FEATURES['aspect_ratios']:
            ratio_diff = abs(width/height - ratio[0]/ratio[1])
            if ratio_diff < 0.1:  # 如果宽高比接近广告常见比例
                ad_score += 1
                break
        
        # 检查颜色饱和度
        if color_variance > 50:  # 高颜色变化通常表示广告
            ad_score += 1
        
        # 检查边缘密度
        if edge_density > 0.15:  # 高边缘密度通常表示广告
            ad_score += 1
        
        # 广告特征得分大于2则判定为广告
        is_ad = ad_score >= 2
        
        return is_ad, features
    
    def _calculate_color_variance(self, image):
        """计算图像的颜色方差"""
        img_array = np.array(image.convert('RGB'))
        variance = np.var(img_array)
        return variance
    
    def _calculate_edge_density(self, image):
        """计算图像的边缘密度"""
        img_bw = image.convert('L')
        img_edges = img_bw.filter(ImageFilter.FIND_EDGES)
        edge_data = np.array(img_edges)
        edge_density = np.sum(edge_data > 100) / (edge_data.shape[0] * edge_data.shape[1])
        return edge_density
    
    def detect_text_in_image(self, image_url):
        """
        检测图像中的文字，判断是否包含广告文本
        这个功能需要OCR库支持，比如Tesseract或百度OCR API
        
        Args:
            image_url: 图像URL
            
        Returns:
            是否包含广告文本，以及检测到的文本
        """
        # 这里是OCR检测的代码
        # 由于需要外部依赖，此处仅返回占位结果
        return False, ""
    
    def is_ad_image(self, image_url, context=None):
        """
        综合判断图片是否为广告图片
        
        Args:
            image_url: 图像URL
            context: 图片的上下文信息，如出现位置、所属栏目等
            
        Returns:
            是否为广告图片
        """
        try:
            # 1. 下载图片
            try:
                response = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response.content))
            except Exception as e:
                logger.error(f"下载或打开图片失败: {image_url}, 错误: {e}")
                return False
            
            # 2. 计算图像哈希
            img_hash = self.compute_image_hash(img)
            
            # 3. 检查是否与已知广告图片相似
            if self.is_similar_to_known_ad(img_hash):
                logger.info(f"检测到已知广告图片: {image_url}")
                self.ad_count += 1
                return True
            
            # 4. 分析图像特征
            is_ad_by_features, features = self.analyze_image_features(img)
            
            # 5. 判断是否为广告
            if is_ad_by_features:
                logger.info(f"根据图像特征判定为广告: {image_url}")
                self.ad_count += 1
                return True
            
            # 6. 如果支持，使用深度学习模型进行检测
            if self.model and TF_AVAILABLE:
                try:
                    is_ad_by_model = self._predict_with_model(img)
                    if is_ad_by_model:
                        logger.info(f"深度学习模型判定为广告: {image_url}")
                        self.ad_count += 1
                        return True
                except Exception as e:
                    logger.error(f"使用深度学习模型预测时出错: {e}")
            
            # 7. 保存到已知广告库（如果确认为广告）
            # 这里可以根据实际需求添加代码，将确认为广告的图片哈希添加到已知广告库
            
            return False
            
        except Exception as e:
            logger.error(f"检测广告图片时出错: {e}, URL: {image_url}")
            return False
    
    def _predict_with_model(self, image):
        """
        使用深度学习模型预测图片是否为广告
        
        Args:
            image: PIL Image对象
            
        Returns:
            模型预测结果（是/否）
        """
        if not self.model or not TF_AVAILABLE:
            return False
        
        try:
            # 图像预处理
            img = image.resize((224, 224))  # 调整为模型输入尺寸
            img_array = np.array(img) / 255.0  # 归一化
            
            # 检查图像通道数
            if len(img_array.shape) == 2:  # 灰度图像
                img_array = np.stack((img_array,) * 3, axis=-1)  # 转换为3通道
            elif img_array.shape[2] == 4:  # RGBA图像
                img_array = img_array[:, :, :3]  # 只保留RGB通道
                
            img_array = np.expand_dims(img_array, axis=0)  # 添加batch维度
            
            # 模型预测
            prediction = self.model.predict(img_array)
            
            # 判断结果
            is_ad = prediction[0][0] > 0.5  # 假设模型输出为[是广告的概率]
            
            return is_ad
        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            return False

# 示例用法
if __name__ == "__main__":
    detector = ImageDetector()
    is_ad = detector.is_ad_image("https://example.com/some_image.jpg")
    print(f"是否为广告图片: {is_ad}") 