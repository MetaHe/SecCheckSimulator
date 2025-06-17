"""
仿真配置文件
将所有可调整的参数集中在此，方便管理和修改。
所有时间单位统一为秒，距离单位为米。
"""

import numpy as np

# ==============================================================================
# 1. 核心仿真参数 (Core Simulation Parameters)
# ==============================================================================
# request.md: "在 3.5 小时（210 分钟）内完成 35,000 人"
TOTAL_SPECTATORS = 35000  # 总观众人数
SIMULATION_DURATION_HOURS = 3.5  # 仿真总时长（小时）
SIMULATION_DURATION_SECONDS = SIMULATION_DURATION_HOURS * 3600  # 仿真总时长（秒）

# 随机种子，用于复现仿真结果
RANDOM_SEED = 42

# ==============================================================================
# 2. 地理与设施参数 (Geography and Facility Parameters)
# ==============================================================================
# --- 关键区域 ---
# request.md: "安检轮候区面积：1080㎡"
WAITING_AREA_SQM = 1080

# request.md: "安检大棚尺寸：15m×6m（单个）"
SECURITY_TENT_SIZE_M = (15, 6)

# --- 公园内路径 ---
# request.md: "路径长度 100-500 米（均匀分布）"
PATH_LENGTH_MIN_M = 100
PATH_LENGTH_MAX_M = 500

# --- 安检设施 ---
# request.md: "安检大棚：南北各 1 组，共 12 条通道"
NUM_SECURITY_TENTS = 2  # 南北两个大棚
LANES_PER_TENT = 15  # 修改：每个大棚15条通道（原6条）
TOTAL_SECURITY_LANES = NUM_SECURITY_TENTS * LANES_PER_TENT

# --- F口结构 ---
# request.md: "内侧下行楼梯：75 级（5 段×15 级），宽 4 米"
STAIRS_WIDTH_M = 4
# request.md: "手扶电梯通行能力：40 人/分钟"
ESCALATOR_CAPACITY_PER_MIN = 40  # 修改：提升至40人/分钟
ESCALATOR_CAPACITY_PER_SEC = ESCALATOR_CAPACITY_PER_MIN / 60
# 电梯物理容量：同时能站多少人（一般扶梯单侧容纳20-30人）
ESCALATOR_PHYSICAL_CAPACITY = 25  # 修改：电梯同时容纳人数
# 电梯队列等候区容量
ESCALATOR_QUEUE_CAPACITY = 160  # 修改：提升至160人容量

# ==============================================================================
# 3. 模块1：交通方式选择 (Transportation Module)
# ==============================================================================
# request.md: "概率分布（示例值，可调整）"
TRANSPORT_PROBS = {
    "自驾": 0.30,
    "公交": 0.40,
    "出租车": 0.15,
    "步行": 0.10,
    "自行车": 0.05
}

# --- 交通延迟 (秒) ---
# request.md: "自驾：正态分布（均值 5 分钟，标准差 2 分钟）"
DRIVE_DELAY_MEAN_S = 5 * 60
DRIVE_DELAY_STD_S = 2 * 60

# request.md: "公交：均匀分布（0-8 分钟）"
BUS_DELAY_MIN_S = 0 * 60
BUS_DELAY_MAX_S = 8 * 60

# --- 群组到达 ---
# request.md: "群组成员安检时间增加 10% 协同延迟"
GROUP_COORDINATION_DELAY_FACTOR = 1.10

# ==============================================================================
# 4. 模块2：公园内步行路径 (Walking Module)
# ==============================================================================
# --- 步行速度 ---
# request.md: "1.2 米/秒（补充，参考行人速度）"
BASE_WALKING_SPEED_MPS = 1.2

# --- 拥挤修正 ---
# request.md: "人流密度 > 0.5 人/㎡ 时...每增 0.1 人/㎡，速度降 10%"
CROWD_DENSITY_THRESHOLD_PPM2 = 0.5
CROWD_DENSITY_INCREMENT_STEP = 0.1
SPEED_REDUCTION_FACTOR_PER_STEP = 0.10

# --- 路径扰动 (秒) ---
# request.md: "单次延迟 1-3 分钟（均匀分布）"
PATH_DISTURBANCE_MIN_S = 1 * 60
PATH_DISTURBANCE_MAX_S = 3 * 60


# ==============================================================================
# 5. 模块3：安检前后疏导 (Security Check & Post-Check Module)
# ==============================================================================
# --- 安检过程 ---
# request.md: "单次安检时间：15 秒（补充，均值）"
# 为增加真实性，我们使用以15秒为中心的指数分布
SECURITY_CHECK_TIME_MEAN_S = 10  # 修改：优化至12秒

# request.md: "安检失败率：2%（补充，随机触发，需重试）"
SECURITY_FAILURE_RATE = 0.02

# request.md: "通道故障率：0.1%（补充，临时故障 2-10 分钟，均匀分布）"
# 注意：此处的故障率定义为"每个观众通过时，通道发生故障的概率"
LANE_FAILURE_PROB_PER_PERSON = 0.001
LANE_FAILURE_DURATION_MIN_S = 2 * 60
LANE_FAILURE_DURATION_MAX_S = 10 * 60

# --- 下行方式选择 ---
# request.md: "初始概率：楼梯 60%，电梯 40%"
DESCEND_INITIAL_PROBS = {"stairs": 0.6, "escalator": 0.4}

# request.md: "动态调整：电梯队列 > 50 人 时，楼梯概率升至 70%"
ESCALATOR_QUEUE_THRESHOLD_FOR_ADJUST = 50
DESCEND_ADJUSTED_PROBS = {"stairs": 0.7, "escalator": 0.3}

# --- 通行能力 ---
# request.md: "楼梯流通率：40 人/分钟/米（宽 4 米时 160 人/分钟）"
STAIRS_THROUGHPUT_PPM_PER_METER = 40
STAIRS_TOTAL_THROUGHPUT_PPM = STAIRS_THROUGHPUT_PPM_PER_METER * STAIRS_WIDTH_M
STAIRS_PERSON_CROSS_TIME_S = 60 / STAIRS_TOTAL_THROUGHPUT_PPM # 单人通过楼梯的平均时间

# ==============================================================================
# 6. 输出设置 (Output Settings)
# ==============================================================================
OUTPUT_FILE_NAME = "outputs/simulation_results.xlsx"
MONITOR_INTERVAL_S = 60  # 每隔60秒记录一次系统状态

# ==============================================================================
# 7. 日志和调试 (Logging and Debugging)
# ==============================================================================
LOG_LEVEL = "INFO"  # "DEBUG" for detailed logs, "INFO" for summary
SPECTATOR_LOG_INTERVAL = 1000 # 每1000个观众打印一次日志

# ============================================================================
# 模块1补丁: 群组到达 (Group Arrival)
# ============================================================================
# 群组规模及概率分布
GROUP_SIZE_PROBS = {
    1: 0.4,  # 单人
    2: 0.3,  # 2人组
    3: 0.2,  # 3人组
    4: 0.1,  # 4人组
}
# 群组安检协同延迟因子 (为 >1 人的群组安检乘以该系数)
GROUP_COORDINATION_DELAY_FACTOR = 1.1 # 增加10%时间

# ============================================================================
# 模块2补丁: 地理与路径 (Geography and Paths)
# ============================================================================
# 定义公园内路径 {名称: {"length": 长度m, "width": 宽度m}}
# 基于示意图和需求文档估算
PATHS = {
    "路径 E (北入口)": {"length": 120, "width": 9},  # E1/E2入口, 估算路径长120m, 平均宽度(8+10)/2=9m
    "路径 B (南入口)": {"length": 55, "width": 10},  # B入口, 估算路径长55m, 宽10m
    "路径 C (其他)": {"length": 300, "width": 7}, # 代表其他更长的路径
}
# 各路径被选择的概率
PATH_CHOICE_PROBS = {
    "路径 E (北入口)": 0.4,
    "路径 B (南入口)": 0.4,
    "路径 C (其他)": 0.2,
}

# ============================================================================
# 模块2补丁: 步行拥挤 (Walking Congestion)
# ============================================================================
# 拥挤修正参数
CONGESTION_DENSITY_THRESHOLD = 0.5  # 触发拥挤降速的密度阈值 (人/㎡)
CONGESTION_SPEED_REDUCTION_UNIT_DENSITY = 0.1 # 密度每增加这么多
CONGESTION_SPEED_REDUCTION_FACTOR = 0.1 # 速度就降低这个比例 (10%)
MIN_WALKING_SPEED_MPS = 0.2 # 拥挤时最低步行速度，避免速度降为0 