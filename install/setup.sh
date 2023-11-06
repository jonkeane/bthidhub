cd /home/pi

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install git -y

git clone https://github.com/jonkeane/bthidhub
cd /home/pi/bthidhub/install/on_rpi
bash ./on_pi_setup.sh
