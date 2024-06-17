# migration_with_kettle
Oracle HR sample database 테이블을 Inforix Table로  마이그레이션하기  위한 Kettle transformation 파일 작성 script입니다.

## 설치 
/home/pentaho 디렉토리에 다음 파일들을 압축해제 합니다.
pdi-ce-9.4.0.0-343.zip
jdk-11.0.2

## Jar File 다운로드
/home/pentaho/data-integration/lib 디렉토리에 다음 파일들을 다운로드 합니다.
config-1.4.0.jar (https://repo1.maven.org/maven2/com/typesafe/config/1.4.0/)
ojdbc8.jar (from oracle)
jdbc-4.50.10.jar ( from IBM informix)

## Python Package Install
pip3 install oracledb
pip3 install jpype1

## 환경변수 설정
pentaho.env 파일 만들고 적용하기
```
export JAVA_HOME=/home/pentaho/jdk-11.0.2
export KETTLE_HOME=/home/pentaho/data-integration
export PATH=$JAVA_HOME/bin:$KETTLE_HOME:$PATH

CLASSPATH=$KETTLE_HOME/classes
for jar in  $KETTLE_HOME/lib/*.jar
do
        CLASSPATH=$jar:$CLASSPATH
done
export CLASSPATH
```
## databae 접속정보
database.conf / spoon.sh 파일로 생성되는 databse정보입니다. 자신의 환경에 맞게 설정하시면 됩니다.
특히 password값.

## 수행 
python3 ktr_oracle_to_informix.py -u hr



