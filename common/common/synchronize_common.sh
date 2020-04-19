# cd $CODE/recommender/backend/common
# cd $CODE/recommender/backend/twitter
# cd $CODE/recommender/backend/xkcd
# cd $CODE/recommender/backend/reddit
# cd $CODE/recommender/backend/news_api
# cd $CODE/recommender/backend/serving
cd $CODE/recommender/backend/common
git pull --rebase origin master && git push origin master
cd $CODE/recommender/backend/twitter
$CODE/recommender/backend/common/synchronize.sh
cd $CODE/recommender/backend/xkcd
$CODE/recommender/backend/common/synchronize.sh
cd $CODE/recommender/backend/reddit
$CODE/recommender/backend/common/synchronize.sh
cd $CODE/recommender/backend/news_api
$CODE/recommender/backend/common/synchronize.sh
cd $CODE/recommender/backend/serving
$CODE/recommender/backend/common/synchronize.sh
