# api
cd /Users/chaopan/PycharmProjects
rm -rf aos-api.tgz
tar -cvzf aos-api.tgz  --exclude=./aos-sizing-api/venv ./aos-sizing-api
#aws s3  --profile ue1  cp aos-api.tgz s3://panchao-data/tmp/
aws s3   cp aos-api.tgz s3://pcd-01/aos-sizing/


sudo su
mkdir -p  /opt/app/aos/ && cd /opt/app/aos/
rm -rf aos-sizing*
aws s3 cp s3://pcd-01/aos-sizing/aos-api.tgz .
tar -xvzf aos-api.tgz
python3 -m venv aos_venv
source aos_venv/bin/activate
pip3 install -r ./aos-sizing-api/requirements.txt
pip3 install numpy
pip3 install fastapi
pip3 install  pandas
pip3 install  loguru
pip3 install jinja2
pip3 install openpyxl
pip3 install uvicorn
nohup python3 aos-sizing-api/app.py >> api.logs 2>&1 &




# web
cd /Users/chaopan/workspace/vscode/naive-ui-admin/
rm -rf dist.tgz
tar -cvzf dist.tgz ./dist/
aws s3  cp dist.tgz s3://pcd-01/aos-sizing/


aws s3 cp s3://pcd-01/aos-sizing/dist.tgz .
rm -rf dist
tar -xvzf dist.tgz
nginx -s reload

yum intstall nginx
# 配置nginx conf
systemctl enable nginx
systemctl start nginx
systemctl status nginx

#./docker-compose rm
#./docker-compose build
#./docker-compose up

#