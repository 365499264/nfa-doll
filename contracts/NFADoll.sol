// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title NFADoll - Non-Fungible Agent Doll
 * @notice BAP-578兼容的AI娃娃养成NFT合约
 * @dev 扩展ERC-721，支持Agent人格状态存储和可验证学习
 */
contract NFADoll is ERC721Enumerable, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    // ========== 数据结构 ==========

    /// @notice Agent元数据 (BAP-578兼容)
    struct AgentMetadata {
        string name;                  // 娃娃名称
        string persona;               // JSON编码的性格特征
        string experience;            // Agent的角色/目的描述
        string voiceHash;             // 语音特征hash
        string animationURI;          // 动画/形象URI
        string vaultURI;              // 链下数据存储URI (IPFS/Arweave)
        bytes32 vaultHash;            // vault内容校验hash
        uint256 createdAt;            // 创建时间
        uint256 lastInteraction;      // 最后互动时间
    }

    /// @notice 学习状态
    struct LearningState {
        bool enabled;                 // 是否启用学习
        bytes32 learningTreeRoot;     // Merkle树根
        uint256 learningVersion;      // 学习版本号
        uint256 lastLearningUpdate;   // 最后学习更新时间
        uint256 totalInteractions;    // 总互动次数
        uint256 totalLearningEvents;  // 总学习事件数
    }

    /// @notice 养成统计 (链上可验证)
    struct GrowthStats {
        uint8 growthStage;            // 0=infant, 1=child, 2=adolescent, 3=adult, 4=elder
        uint256 rarityScore;          // 稀有度评分
        uint8 hiddenTraitsCount;      // 解锁的隐藏特质数量
        uint256 deepConversations;    // 深度对话次数
        uint256 topicsExplored;       // 探索的话题数
    }

    // ========== 存储 ==========

    mapping(uint256 => AgentMetadata) public agents;
    mapping(uint256 => LearningState) public learningStates;
    mapping(uint256 => GrowthStats) public growthStats;
    mapping(uint256 => address) public agentLogic;          // 逻辑合约地址
    mapping(address => bool) public approvedLearningModules; // 已批准的学习模块

    // 交易市场相关
    mapping(uint256 => uint256) public listingPrices;       // 挂牌价格
    mapping(uint256 => bool) public isListed;               // 是否在市场上

    // 费用
    uint256 public mintFee = 0.01 ether;                    // 铸造费用
    uint256 public marketplaceFee = 250;                    // 2.5% 市场手续费 (basis points)

    // ========== 事件 ==========

    event AgentCreated(
        uint256 indexed tokenId,
        address indexed owner,
        string name,
        uint256 timestamp
    );

    event LearningEnabled(
        uint256 indexed tokenId,
        uint256 timestamp
    );

    event LearningTreeUpdated(
        uint256 indexed tokenId,
        bytes32 newTreeRoot,
        uint256 version,
        uint256 timestamp
    );

    event GrowthStageChanged(
        uint256 indexed tokenId,
        uint8 oldStage,
        uint8 newStage,
        uint256 timestamp
    );

    event HiddenTraitUnlocked(
        uint256 indexed tokenId,
        string traitId,
        uint256 timestamp
    );

    event AgentListed(
        uint256 indexed tokenId,
        uint256 price,
        address indexed seller
    );

    event AgentSold(
        uint256 indexed tokenId,
        address indexed seller,
        address indexed buyer,
        uint256 price
    );

    event AgentDelisted(
        uint256 indexed tokenId
    );

    // ========== 修饰符 ==========

    modifier onlyAgentOwner(uint256 tokenId) {
        require(ownerOf(tokenId) == msg.sender, "Not agent owner");
        _;
    }

    modifier agentExists(uint256 tokenId) {
        require(_exists(tokenId), "Agent does not exist");
        _;
    }

    // ========== 构造函数 ==========

    constructor() ERC721("NFA Doll", "NFADOLL") Ownable(msg.sender) {}

    // ========== 铸造 ==========

    /**
     * @notice 铸造一个新的AI娃娃Agent
     * @param name 娃娃名称
     * @param persona 初始性格JSON
     * @param vaultURI 链下存储URI
     */
    function mintAgent(
        string calldata name,
        string calldata persona,
        string calldata vaultURI
    ) external payable returns (uint256) {
        require(msg.value >= mintFee, "Insufficient mint fee");

        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();

        _safeMint(msg.sender, newTokenId);

        // 初始化Agent元数据
        agents[newTokenId] = AgentMetadata({
            name: name,
            persona: persona,
            experience: "",
            voiceHash: "",
            animationURI: "",
            vaultURI: vaultURI,
            vaultHash: bytes32(0),
            createdAt: block.timestamp,
            lastInteraction: block.timestamp
        });

        // 初始化学习状态 (默认启用)
        learningStates[newTokenId] = LearningState({
            enabled: true,
            learningTreeRoot: bytes32(0),
            learningVersion: 0,
            lastLearningUpdate: block.timestamp,
            totalInteractions: 0,
            totalLearningEvents: 0
        });

        // 初始化养成统计
        growthStats[newTokenId] = GrowthStats({
            growthStage: 0,     // infant
            rarityScore: 0,
            hiddenTraitsCount: 0,
            deepConversations: 0,
            topicsExplored: 0
        });

        emit AgentCreated(newTokenId, msg.sender, name, block.timestamp);

        return newTokenId;
    }

    // ========== 学习更新 ==========

    /**
     * @notice 更新Agent的学习树 (核心养成功能)
     * @param tokenId Agent的tokenId
     * @param newTreeRoot 新的Merkle树根
     * @param interactionCount 新增互动次数
     * @param learningEventCount 新增学习事件数
     */
    function updateLearningTree(
        uint256 tokenId,
        bytes32 newTreeRoot,
        uint256 interactionCount,
        uint256 learningEventCount
    ) external onlyAgentOwner(tokenId) agentExists(tokenId) {
        LearningState storage state = learningStates[tokenId];
        require(state.enabled, "Learning not enabled");

        // 更新学习状态
        state.learningTreeRoot = newTreeRoot;
        state.learningVersion++;
        state.lastLearningUpdate = block.timestamp;
        state.totalInteractions += interactionCount;
        state.totalLearningEvents += learningEventCount;

        // 更新最后互动时间
        agents[tokenId].lastInteraction = block.timestamp;

        emit LearningTreeUpdated(
            tokenId,
            newTreeRoot,
            state.learningVersion,
            block.timestamp
        );
    }

    /**
     * @notice 更新养成统计
     */
    function updateGrowthStats(
        uint256 tokenId,
        uint8 newGrowthStage,
        uint256 newRarityScore,
        uint8 newHiddenTraitsCount,
        uint256 newDeepConversations,
        uint256 newTopicsExplored
    ) external onlyAgentOwner(tokenId) agentExists(tokenId) {
        GrowthStats storage stats = growthStats[tokenId];

        // 检查成长阶段是否变化
        if (newGrowthStage != stats.growthStage) {
            emit GrowthStageChanged(
                tokenId,
                stats.growthStage,
                newGrowthStage,
                block.timestamp
            );
        }

        stats.growthStage = newGrowthStage;
        stats.rarityScore = newRarityScore;
        stats.hiddenTraitsCount = newHiddenTraitsCount;
        stats.deepConversations = newDeepConversations;
        stats.topicsExplored = newTopicsExplored;
    }

    /**
     * @notice 更新性格数据 (persona JSON)
     */
    function updatePersona(
        uint256 tokenId,
        string calldata newPersona
    ) external onlyAgentOwner(tokenId) agentExists(tokenId) {
        agents[tokenId].persona = newPersona;
        agents[tokenId].lastInteraction = block.timestamp;
    }

    /**
     * @notice 更新vault数据
     */
    function updateVault(
        uint256 tokenId,
        string calldata newVaultURI,
        bytes32 newVaultHash
    ) external onlyAgentOwner(tokenId) agentExists(tokenId) {
        agents[tokenId].vaultURI = newVaultURI;
        agents[tokenId].vaultHash = newVaultHash;
    }

    // ========== 交易市场 ==========

    /**
     * @notice 将Agent挂牌出售
     */
    function listAgent(
        uint256 tokenId,
        uint256 price
    ) external onlyAgentOwner(tokenId) agentExists(tokenId) {
        require(price > 0, "Price must be > 0");
        require(!isListed[tokenId], "Already listed");

        // 需要授权合约转移
        require(
            getApproved(tokenId) == address(this) ||
            isApprovedForAll(msg.sender, address(this)),
            "Contract not approved for transfer"
        );

        listingPrices[tokenId] = price;
        isListed[tokenId] = true;

        emit AgentListed(tokenId, price, msg.sender);
    }

    /**
     * @notice 购买Agent
     */
    function buyAgent(
        uint256 tokenId
    ) external payable agentExists(tokenId) {
        require(isListed[tokenId], "Agent not listed");
        require(msg.value >= listingPrices[tokenId], "Insufficient payment");

        address seller = ownerOf(tokenId);
        require(msg.sender != seller, "Cannot buy own agent");

        uint256 price = listingPrices[tokenId];

        // 计算手续费
        uint256 fee = (price * marketplaceFee) / 10000;
        uint256 sellerProceeds = price - fee;

        // 清除挂牌
        isListed[tokenId] = false;
        listingPrices[tokenId] = 0;

        // 转移NFT
        _transfer(seller, msg.sender, tokenId);

        // 转移资金
        payable(seller).transfer(sellerProceeds);

        // 退还多余的支付
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }

        emit AgentSold(tokenId, seller, msg.sender, price);
    }

    /**
     * @notice 取消挂牌
     */
    function delistAgent(
        uint256 tokenId
    ) external onlyAgentOwner(tokenId) {
        require(isListed[tokenId], "Not listed");

        isListed[tokenId] = false;
        listingPrices[tokenId] = 0;

        emit AgentDelisted(tokenId);
    }

    // ========== 查询函数 ==========

    /**
     * @notice 获取Agent的完整信息
     */
    function getAgentInfo(uint256 tokenId) external view agentExists(tokenId)
        returns (
            AgentMetadata memory metadata,
            LearningState memory learning,
            GrowthStats memory growth,
            address owner,
            bool listed,
            uint256 price
        )
    {
        return (
            agents[tokenId],
            learningStates[tokenId],
            growthStats[tokenId],
            ownerOf(tokenId),
            isListed[tokenId],
            listingPrices[tokenId]
        );
    }

    /**
     * @notice 获取市场上所有挂牌的Agent
     */
    function getListedAgents() external view returns (uint256[] memory) {
        uint256 total = totalSupply();
        uint256 listedCount = 0;

        // 先计数
        for (uint256 i = 1; i <= total; i++) {
            if (isListed[i]) listedCount++;
        }

        // 填充数组
        uint256[] memory listed = new uint256[](listedCount);
        uint256 index = 0;
        for (uint256 i = 1; i <= total; i++) {
            if (isListed[i]) {
                listed[index] = i;
                index++;
            }
        }

        return listed;
    }

    /**
     * @notice 获取某用户拥有的所有Agent
     */
    function getAgentsByOwner(address owner) external view returns (uint256[] memory) {
        uint256 balance = balanceOf(owner);
        uint256[] memory tokens = new uint256[](balance);
        for (uint256 i = 0; i < balance; i++) {
            tokens[i] = tokenOfOwnerByIndex(owner, i);
        }
        return tokens;
    }

    /**
     * @notice 验证学习历史的Merkle证明
     */
    function verifyLearningProof(
        uint256 tokenId,
        bytes32 leaf,
        bytes32[] calldata proof
    ) external view agentExists(tokenId) returns (bool) {
        bytes32 computedHash = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];
            if (computedHash <= proofElement) {
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }
        return computedHash == learningStates[tokenId].learningTreeRoot;
    }

    // ========== 管理函数 ==========

    function setMintFee(uint256 newFee) external onlyOwner {
        mintFee = newFee;
    }

    function setMarketplaceFee(uint256 newFee) external onlyOwner {
        require(newFee <= 1000, "Fee too high"); // 最高10%
        marketplaceFee = newFee;
    }

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    function _exists(uint256 tokenId) internal view returns (bool) {
        return tokenId > 0 && tokenId <= _tokenIds.current() && _ownerOf(tokenId) != address(0);
    }
}
