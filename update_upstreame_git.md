git fetch upstream

# 3. 合并上游到你的分支，遇到冲突时使用你的版本
git merge upstream/main --strategy-option ours

# 或者更精确地控制
git merge upstream/main -X ours

# 4. 推送到你的远程仓库
git push origin main
