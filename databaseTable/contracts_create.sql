CREATE TABLE `contracts` (
  `id` varchar(50) DEFAULT NULL,
  `COMPANY_NAME` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NOT NULL COMMENT '公司',
  `fdate` date NOT NULL COMMENT '日期',
  `SIGNED_SETS` int NOT NULL COMMENT '签约套数',
  `SIGNED_AREA` decimal(16,2) NOT NULL COMMENT '签约面积',
  `SIGNED_AMOUNT` decimal(16,2) NOT NULL COMMENT '签约金额',
  PRIMARY KEY (`COMPANY_NAME`,`fdate`),
  KEY `id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='签约表'