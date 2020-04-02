tmp=$(pwd)
cd $CODE/recommender/backend/common
git add -A .
git commit -m $1
git push origin master
cd $tmp
git subrepo pull common
