import os
from fastapi import FastAPI, HTTPException
from influxdb_client import InfluxDBClient, Point
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

influx_token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG")
bucket = os.getenv("INFLUXDB_BUCKET")
url = os.getenv("INFLUXDB_URL", "http://localhost:8086")

client = InfluxDBClient(url=url, token=influx_token, org=org)
write_api = client.write_api()
query_api = client.query_api()


class DataPoint(BaseModel):
    measurement: str
    value: float
    timestamp: Optional[datetime] = None


@app.post("/write")
def write_data(data: DataPoint):
    try:
        point = (
            Point(data.measurement)
            .field("value", data.value)
            .time(data.timestamp or datetime.now(tz=timezone.utc))
        )
        write_api.write(bucket=bucket, org=org, record=point)
        return {"status": "success", "message": "Data written to InfluxDB"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing data: {e}")


@app.get("/query")
def query_data(measurement: str, start: str, stop: str):
    try:
        query = f"""
            from(bucket: "{bucket}")
                |> range(start: {start}, stop: {stop})
                |> filter(fn: (r) => r._measurement == "{measurement}")
        """
        result = query_api.query(org=org, query=query)
        data = []

        for table in result:
            for record in table.records:
                data.append(
                    {
                        "time": record.get_time(),
                        "value": record.get_value(),
                    }
                )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying data: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
