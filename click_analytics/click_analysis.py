from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext

import json


def main():
    spark = SparkSession.Builder().appName("ClickAnalytics").getOrCreate()
    _ = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "stream_analytics")
        .load()
        .writeStream.foreach(lambda x: print("value:", x.asDict()))
        .start()
        .awaitTermination()
    )


if __name__ == "__main__":
    main()
