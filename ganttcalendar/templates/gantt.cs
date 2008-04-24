<?cs include "header.cs" ?>
<?cs include "macros.cs" ?>

<style>
table.list {
    width:100%;
    border-collapse: collapse;
    margin-bottom: 6px;
}

table.with-cells td {
    border: 1px solid #d7d7d7;
}

table.list td {
    padding:2px;
}

table.list thead th {
    text-align: center;
    background: #eee;
    border: 1px solid #d7d7d7;
    color: #777;
}

table.list tbody th {
    font-weight: bold;
    background: #eed;
    border: 1px solid #d7d7d7;
    color: #777;
}

.tip {
  display: none; text-align:left;
}

.ticket {
  font-size: 9px;
}


.textright {
  text-align:right;
}

.active {
   background-color:#fff;
}
.holiday {
   background-color: #f6f7f8;
   color: red;
}
.today {
   background-color: #ffe0e0;
}

div.ticket:hover span.tip{
  display:block;
  position:absolute;
  border:1px solid #555;
  background-color: #ffe;
  font-size: 8pt;
  top: 12pt;
  left:12pt;
  z-index: 100;
}


.ticket_late { background:pink url(../images/ticket_late.png); border: 1px solid red; }
.ticket_done { background:lightgreen url(../images/ticket_done.png); border: 1px solid green; }  
.ticket_todo { background:lightgrey url(../images/ticket_todo.png); border: 1px solid gray; }

.ticket {
  position: absolute;
  height:8px;
  color:black;
}

.title {
  overflow: hidden;
  position: absolute;
  line-height: 1.2em; 
}

.baseline {
  border-left: 1px dashed red;
  position: absolute; 
}

.milestone {
  border-left: 2px solid red;
  position: absolute; 
}

.line {
  border-left: 1px solid gray;
  border-top: 1px solid gray;
  position: absolute; 
}

.gantt_tbl {
  border-top: 1px solid gray;
  border-bottom: 1px solid gray;
  border-right: 1px solid gray;
  border-left: 1px solid gray;
}

.gantt_hdr {
  position:absolute;
  top:0;
  height:14px;
  border-top: 1px solid gray;
  border-bottom: 1px solid gray;
  border-right: 1px solid gray;
  border-left: 1px solid gray;
  background-color: #eee;
  text-align: center;
  overflow: hidden;
}
</style>

<form>
<table class="list">
  <tr>
    <td>
        <input type="button" value="&lt;&lt;<?cs var:gan.prev.month ?>月" onclick="form.year.value = <?cs var:gan.prev.year ?>; form.month.value = <?cs var:gan.prev.month ?>; form.submit();"/>
    </td>
    <td align="center">
      <select name="year">
        <?cs loop:y = "2002", "2012", "1" ?>
        <option value="<?cs var:y ?>" <?cs if:y == gan.current.year ?>selected<?cs /if ?>><?cs var:y ?></option>
        <?cs /loop ?>
      </select>
      年
      <select name="month">
        <?cs loop:m = "1", "12", "1" ?>
        <option value="<?cs var:m ?>" <?cs if:m == gan.current.month ?>selected<?cs /if ?>><?cs var:m ?></option>
        <?cs /loop ?>
      </select>
      月　
　　　基準日<input type="text" name="baseday" value="<?cs var:gan.baseday.year ?>/<?cs var:gan.baseday.month ?>/<?cs var:gan.baseday.day ?>" length="10"/>
    </td>
    <td align="right">
       <input type="button" value="<?cs var:gan.next.month ?>月&gt;&gt;" onclick="form.year.value = <?cs var:gan.next.year ?>; form.month.value = <?cs var:gan.next.month ?>; form.submit();"/>
    </td>
  </tr>
  <tr>
    <td>
    </td>
    <td>
      <table>
      <tr>
        <td>ソートするフィールド</td>
        <td width="150px">
　        <select name="sorted_field">
            <option value="component" <?cs if:gan.sorted_field == 'component' ?>selected<?cs /if ?>>component</option>
            <option value="milestone" <?cs if:gan.sorted_field == 'milestone' ?>selected<?cs /if ?>>milestone</option>
          </select>
        </td>
        <td>
          <input type="checkbox" name="show_my_ticket" value="on" <?cs if:gan.show_my_ticket == "on" ?>checked<?cs /if ?> />自分のチケットのみ表示
        </td>
      </tr>
      <tr>
        <td><?cs var:gan.sorted_field ?></td>
        <td width="150px">
　        <select name="selected_item">
            <?cs each:i = gan.items ?>
            <option value="<?cs var:i.name ?>" <?cs if:gan.selected_item == i.name ?>selected<?cs /if ?>><?cs var:i.name ?></option>
            <?cs /each ?>
          </select>
        </td>
        <td>
          <input type="checkbox" name="show_closed_ticket" value="on" <?cs if:gan.show_closed_ticket == "on" ?>checked<?cs /if ?> />closeしたチケットを表示
        </td>
      </tr>
      </table>
    </td>
    <td align="right" valign="bottom">
      <input type="submit" value="更新" />
    </td>
  </tr>
</table>

<!-- gantt -->
<?cs set:offset = 0 ?>
<?cs set:dw = gan.graph.dw ?>
<?cs set:ti = gan.graph.ti ?>
<?cs set:first = gan.graph.first ?>
<?cs set:base = gan.graph.base ?>
<?cs set:term = gan.graph.term ?>
<?cs set:numticket = gan.graph.numticket ?>

<table style="width: 100%;">
<tr style="height: <?cs var:numticket * ti + 110 ?>px;">
  <td style="width: 300px;" valign="top">
    <!-- line left of milestone -->
    <div style="overflow: none; position: relative; height: <?cs var:numticket * ti + 110 ?>px;">
      <!-- line between milestone and ticket -->
      <div style="position: absolute; top: 0px; left: 0px; width: 88px; height:<?cs var:numticket * ti + 70 ?>px; border-top: 1px solid gray; border-bottom: 1px solid gray; border-right: 1px solid gray; border-left: 1px solid gray;"></div>
      <!-- line between ticket and owner -->
      <div style="position: absolute; top: 0px; left: 0px; width: 192px; height:<?cs var:numticket * ti + 70 ?>px; border-top: 1px solid gray; border-bottom: 1px solid gray; border-right: 1px solid gray; border-left: 1px solid gray;"></div>
      <!-- line right of owner -->
      <div style="position: relative; top: 0px; left: 0px; width: 300px; height:<?cs var:numticket * ti + 70 ?>px; border-top: 1px solid gray; border-bottom: 1px solid gray; border-right: 1px solid gray; border-left: 1px solid gray;"></div>
      <div style="top:0px; left: 0px; width: 89px; height: 44px" class="gantt_hdr">
        <?cs var:gan.sorted_field ?>
      </div>
      <div style="top:0px; left: 89px; width: 104px; height: 44px" class="gantt_hdr">チケット</div>
      <div style="top:0px; left: 193px; width: 107px; height: 44px" class="gantt_hdr">担当者</div>

<?cs set:offset = 0 ?>
<?cs set:item = None ?>

<?cs each:t = gan.tickets ?>
<span>

  <!-- draw ticket label -->
  <?cs if:t.ticket[gan.sorted_field] != item ?>
  <div style="top: <?cs var:offset * ti + 60 ?>px; left: 4px; width: 92px" class="ticket" >
    <?cs var:t.ticket[gan.sorted_field] ?>
  </div>
  <?cs /if ?>

<?cs set:item = t.ticket[gan.sorted_field] ?>

  <div style="top: <?cs var:offset * ti + 60 ?>px; left: 92px; width: 100px;" class="ticket" >
    <span class="tip">
      <pre><span class="type"><?cs var:t.ticket['type'] ?></span>#<?cs var:t.ticket['id'] ?>: <?cs var:t.ticket['summary'] ?></pre>
      <strong>担当者</strong>: <?cs var:t.ticket['owner'] ?><br />
      <strong>開始日</strong>: <?cs var:t.ticket['due_assign'] ?><br />
      <strong>終了日</strong>: <?cs var:t.ticket['due_close'] ?><br />
      <strong>達成率</strong>: <?cs var:t.ticket['complete'] ?>%<br />
      <strong>詳細</strong>: <pre><?cs var:t.ticket['description'] ?></pre>
    </span>
    <a href="<?cs var:t.url ?>">#<?cs var:t.ticket['id'] ?>:<?cs var:t.short_summary ?></a>
  </div>
  <div style="top: <?cs var:offset * ti + 60 ?>px; left: 196px;" class="ticket" >
  <?cs var:t.ticket['owner'] ?>
  </div>

<?cs set:offset = offset + 1 ?>

<br />
</span>
<?cs /each ?>

    </div>
  </td>
  <td  valign="top">
    <div style="overflow: auto; position: relative; height: <?cs var:numticket * ti + 110 ?>px;" >
      <small>

<?cs set:offset = 0 ?>

      <!-- day -->
      <?cs if:dw > 11 ?>
      <?cs loop:d = #0, term - #1, #1 ?>
      <?cs set:cur.year = gan.graph.cdays[d].year ?>
      <?cs set:cur.month = gan.graph.cdays[d].month ?>
      <?cs set:cur.day = gan.graph.cdays[d].day ?>
      <?cs set:cur.weekday = gan.graph.cdays[d].weekday ?>
      <?cs set:cur.monthrange = gan.graph.cdays[d].monthrange ?>
      <span>
        <div style="top:30px; left: <?cs var:offset * dw ?>px; width: <?cs var:dw ?>px;" class="gantt_hdr">
          <?cs var:gan.weekdays[cur.weekday] ?><br /><?cs var:cur.day ?>
        </div>
        <?cs if:cur.weekday > 4 ?>
        <div style="top:45px; left: <?cs var:d * dw ?>px; width: <?cs var:dw ?>px; height: <?cs var:(numticket + 1) * ti ?>px;" class="gantt_hdr">
        </div>
        <?cs /if ?>

        <!-- week -->
        <?cs if:cur.weekday == 6 ?>
        <span>
          <?cs if:(term - d) >= 7 ?>
          <div style="top:15px; left: <?cs var:d * dw ?>px; width: <?cs var:dw * 7 ?>px;" class="gantt_hdr">
            <?cs var:cur.month ?>/<?cs var:cur.day ?>
          </div>
          <?cs /if ?>
          <?cs if:(term - d) < 7 ?>
          <div style="top:15px; left: <?cs var:d * dw ?>px; width: <?cs var:(term - d) * dw ?>px;" class="gantt_hdr"></div>
          <?cs /if ?>
          <?cs if:d < 7 ?>
          <div style="top:15px; left: 0px; width: <?cs var:offset * dw ?>px;" class="gantt_hdr"></div>
          <?cs /if ?>
        </span>
        <?cs /if ?>

        <!-- month -->
        <?cs if:cur.day == 1 ?>
        <span>
          <div style="top:0px; left: <?cs var:d * dw ?>px; width: <?cs var:cur.monthrange * dw ?>px;" class="gantt_hdr">
            <?cs var:cur.year ?>/<?cs var:cur.month ?>
          </div>
        </span>
        <?cs /if ?>

        <!-- left line of chart -->
        <div class="line" style="height: <?cs var:(numticket + 1) * ti ?>px; top: 45px; left: 0px; width: 1px;">&nbsp;</div>
        <!-- right line of chart -->
        <div style="position: absolute; border-left: 1px solid gray; height: <?cs var:(numticket + 1) * ti ?>px; top: 45px; left: <?cs var:term * dw + 1 ?>px; width: 1px;">&nbsp;</div>
        <!-- bottom line of chart -->
        <div style="position: absolute; border-top: 1px solid gray; height: 1px; top: <?cs var:(numticket + 1) * ti + 46 ?>px; left: 0px; width: <?cs var:term * dw + 1 ?>px;">&nbsp;</div>

<?cs set:offset = offset + 1 ?>

      </span>
      <?cs /loop ?>
      <?cs /if ?>

<!-- tickets -->
<?cs set:offset = 0 ?>

<?cs each:t = gan.tickets ?>
      <span>

        <!-- draw chart -->
        <?cs if:t.assign != -1 && t.todow > 0 ?>
        <div style="top: <?cs var:offset * ti + 60 ?>px; left: <?cs var:t.assign * dw ?>px; width: <?cs var:t.todow ?>px;" class="ticket ticket_todo"></div>
        <?cs /if ?>
        <?cs if:t.latew > 0 && t.assign != -1 ?>
        <div style="top: <?cs var:offset * ti + 60 ?>px; left: <?cs var:t.assign * dw ?>px; width: <?cs var:t.latew ?>px;" class="ticket ticket_late"></div>
        <?cs /if ?>
        <?cs if:t.complete > 0 && t.assign != -1 ?>
        <div style="top: <?cs var:offset * ti + 60 ?>px; left: <?cs var:t.assign * dw ?>px; width: <?cs var:t.complete ?>px;" class="ticket ticket_done"></div>
        <?cs /if ?>

<?cs set:offset = offset + 1 ?>

      </span>
<?cs /each ?>

      </small>

      <!-- draw baseline -->
      <?cs if:base + 1 < term ?>
      <div class="baseline" style="top: 45px; height: <?cs var:(numticket + 1) * ti ?>px; left: <?cs var:(base + 1) * dw ?>px; width: 10px;">&nbsp;</div>
      <?cs /if ?>

      <?cs set:m_line = gan.graph.m_line ?>
      <?cs if:m_line != -1 && m_line + 1 < term ?>
      <div class="milestone" style="top: 45px; height: <?cs var:(numticket + 1) * ti ?>px; left: <?cs var:(m_line + 2) * dw ?>px; width: 10px;">&nbsp;</div>
      <?cs /if ?>
    </div>
  </td>
</tr>
</table>
</form>
<!-- gantt -->

<?cs include "footer.cs" ?>
