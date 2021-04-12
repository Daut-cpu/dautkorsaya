# dautkorsaya
<!DOCTYPE html>
<html>
<head>
<script>
function startTime() {
  var day = new Date();
  var hour = day.getHours();
  var minute = day.getMinutes();
  var second = day.getSeconds();
  minute = checkTime(minute);
  second = checkTime(second);
  document.getElementById('txt').innerHTML =
  hour + ":" + minute + ":" + second;
  var t = setTimeout(startTime, 500);
}
function checkTime(i) {
  if (i < 10) {i = "0" + i};  // add zero in front of numbers < 10
  return i;
}
</script>
</head>

<body onload="startTime()">

<div id="txt"></div>

</body>
</html>
