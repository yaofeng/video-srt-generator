"""
VAD (Voice Activity Detection) 测试脚本

测试 fsmn-vad 模型的语音活动检测功能，
并验证不同格式的输出结果解析
"""
import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_vad():
    """测试 VAD 模型"""
    try:
        from funasr import AutoModel
        import soundfile as sf
        import numpy as np

        # 音频文件路径
        audio_path = Path("/home/ubuntu/workspace/video-srt-generator/backend/outputs/180e9552-480c-45cd-8859-ac9d63ed92c6_audio.wav")

        if not audio_path.exists():
            logger.error(f"音频文件不存在: {audio_path}")
            return

        logger.info(f"开始测试 VAD，音频文件: {audio_path}")

        # 加载模型
        logger.info("加载 fsmn-vad 模型...")
        model = AutoModel(
            model="fsmn-vad",
            model_revision="v2.0.4",
            device="cuda"  # 如果没有 CUDA，会自动回退到 CPU
        )
        logger.info("fsmn-vad 模型加载成功")

        # 加载音频
        logger.info("加载音频文件...")
        waveform, sample_rate = sf.read(str(audio_path))
        logger.info(f"原始音频: shape={waveform.shape}, sample_rate={sample_rate}, 时长={len(waveform)/sample_rate:.2f}秒")

        # 确保单声道
        if len(waveform.shape) > 1:
            logger.info(f"转换为单声道，原始通道数: {waveform.shape[1]}")
            waveform = waveform[:, 0]

        # 重采样到 16kHz（fsmn-vad 要求）
        if sample_rate != 16000:
            from scipy import signal
            logger.info(f"重采样从 {sample_rate}Hz 到 16000Hz")
            number_of_samples = round(len(waveform) * float(16000) / sample_rate)
            waveform = signal.resample(waveform, number_of_samples)
            sample_rate = 16000

        logger.info(f"处理后音频: shape={waveform.shape}, sample_rate={sample_rate}, 时长={len(waveform)/sample_rate:.2f}秒")

        # 使用 fsmn-vad 进行语音活动检测
        logger.info("=" * 80)
        logger.info("开始 VAD 检测...")
        logger.info("=" * 80)

        vad_result = model.generate(
            input=[waveform],
            batch_size_s=300  # 5 分钟批量处理
        )

        logger.info(f"VAD 结果类型: {type(vad_result)}")
        logger.info(f"VAD 结果数量: {len(vad_result) if vad_result else 0}")

        if not vad_result or len(vad_result) == 0:
            logger.warning("VAD 返回空结果")
            return

        # 分析第一个结果
        result = vad_result[0]
        logger.info(f"第一个结果类型: {type(result)}")
        logger.info(f"第一个结果内容: {result}")

        # 尝试不同的解析方式
        segments = []

        # 方式1: sentence_info
        if isinstance(result, dict):
            logger.info("\n" + "=" * 80)
            logger.info("尝试解析为字典格式...")
            logger.info("=" * 80)
            logger.info(f"字典键: {list(result.keys())}")

            if 'sentence_info' in result:
                logger.info("找到 'sentence_info' 键")
                sentence_info = result['sentence_info']
                logger.info(f"sentence_info 类型: {type(sentence_info)}")
                logger.info(f"sentence_info 长度: {len(sentence_info) if sentence_info else 0}")

                if sentence_info:
                    for i, item in enumerate(sentence_info[:20]):  # 只显示前20个
                        logger.info(f"  片段 {i+1}: {item}")
                        if isinstance(item, dict):
                            start_ms = item.get('start', 0)
                            end_ms = item.get('end', 0)
                            duration_s = (end_ms - start_ms) / 1000.0
                            segments.append((start_ms / 1000.0, end_ms / 1000.0))
                            logger.info(f"    时间: {start_ms}ms - {end_ms}ms ({duration_s:.2f}s)")

            if 'value' in result:
                logger.info("找到 'value' 键")
                value = result['value']
                logger.info(f"value 类型: {type(value)}")
                logger.info(f"value 长度: {len(value) if value else 0}")

                if value:
                    for i, item in enumerate(value):
                        logger.info(f"  片段 {i+1}: {item}")
                        # VAD 返回的可能是列表格式 [start_ms, end_ms]
                        if isinstance(item, list) and len(item) == 2:
                            start_ms = item[0]
                            end_ms = item[1]
                            duration_s = (end_ms - start_ms) / 1000.0
                            segments.append((start_ms / 1000.0, end_ms / 1000.0))
                            logger.info(f"    时间: {start_ms}ms - {end_ms}ms ({duration_s:.2f}s)")
                        # 或者是字典格式 {'start': ms, 'end': ms}
                        elif isinstance(item, dict):
                            start_ms = item.get('start', 0)
                            end_ms = item.get('end', 0)
                            duration_s = (end_ms - start_ms) / 1000.0
                            segments.append((start_ms / 1000.0, end_ms / 1000.0))
                            logger.info(f"    时间: {start_ms}ms - {end_ms}ms ({duration_s:.2f}s)")

        # 方式2: 列表格式
        elif isinstance(result, list):
            logger.info("\n" + "=" * 80)
            logger.info("尝试解析为列表格式...")
            logger.info("=" * 80)
            logger.info(f"列表长度: {len(result)}")

            for i, item in enumerate(result):
                logger.info(f"  片段 {i+1}: {item}")
                # VAD 返回的可能是列表格式 [start_ms, end_ms]
                if isinstance(item, list) and len(item) == 2:
                    start_ms = item[0]
                    end_ms = item[1]
                    duration_s = (end_ms - start_ms) / 1000.0
                    segments.append((start_ms / 1000.0, end_ms / 1000.0))
                    logger.info(f"    时间: {start_ms}ms - {end_ms}ms ({duration_s:.2f}s)")
                # 或者是字典格式 {'start': ms, 'end': ms}
                elif isinstance(item, dict):
                    start_ms = item.get('start', 0)
                    end_ms = item.get('end', 0)
                    duration_s = (end_ms - start_ms) / 1000.0
                    segments.append((start_ms / 1000.0, end_ms / 1000.0))
                    logger.info(f"    时间: {start_ms}ms - {end_ms}ms ({duration_s:.2f}s)")
                else:
                    logger.info(f"    类型: {type(item)}")

        else:
            logger.warning(f"未知的 VAD 结果格式: {type(result)}")

        # 汇总结果
        logger.info("\n" + "=" * 80)
        logger.info("VAD 检测结果汇总")
        logger.info("=" * 80)
        logger.info(f"检测到 {len(segments)} 个语音片段")

        if segments:
            total_speech_time = sum([e - s for s, e in segments])
            total_audio_time = len(waveform) / sample_rate

            logger.info(f"总语音时长: {total_speech_time:.2f}秒")
            logger.info(f"总音频时长: {total_audio_time:.2f}秒")
            logger.info(f"语音占比: {total_speech_time/total_audio_time*100:.1f}%")

            logger.info(f"\n前 10 个片段:")
            for i, (s, e) in enumerate(segments[:10]):
                logger.info(f"  {i+1}. {s:.2f}s - {e:.2f}s (时长: {e-s:.2f}s)")

            # 计算间隔
            if len(segments) > 1:
                logger.info(f"\n片段间隔:")
                for i in range(len(segments) - 1):
                    gap = segments[i+1][0] - segments[i][1]
                    if gap > 0:
                        logger.info(f"  片段 {i+1} -> {i+2}: 间隔 {gap:.2f}秒")
                    else:
                        logger.info(f"  片段 {i+1} -> {i+2}: 无间隔（重叠）")
        else:
            logger.warning("没有检测到语音片段，将整个音频作为单一片段处理")
            total_duration = len(waveform) / sample_rate
            segments = [(0.0, total_duration)]
            logger.info(f"单一片段: 0.0s - {total_duration:.2f}s")

    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保已安装以下依赖:")
        logger.error("  - funasr")
        logger.error("  - soundfile")
        logger.error("  - numpy")
        logger.error("  - scipy")
    except Exception as e:
        logger.exception(f"VAD 测试失败: {e}")


if __name__ == '__main__':
    asyncio.run(test_vad())
