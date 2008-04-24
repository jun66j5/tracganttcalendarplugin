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
   color: black;
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
  z-index: 100;
}

body { behavior:url("<?cs var:cal.behavior_url ?>"); }
</style>

<form>
<table class="list">
  <tr>
    <td>
    </td>
    <td>
　      マイルストーン<select name="selected_milestone">
             <?cs each:m = cal.milestones ?>
             <option value="<?cs var:m.name ?>" <?cs if:m.name == cal.selected_milestone ?>selected<?cs /if ?>><?cs var:m.name ?></option>
             <?cs /each ?>
        </select>
　　    <input type="checkbox" name="show_my_ticket" <?cs if:cal.show_my_ticket ?>checked<?cs /if ?> />自分のチケットのみ表示
    </td>
    <td align="right">
　　    <input type="submit" value="更新" />
    </td>
  </tr>
  <tr>
    <td>
        <input type="button" value="&lt;&lt;<?cs var:cal.prev.month ?>月" onclick="form.year.value = <?cs var:cal.prev.year ?>; form.month.value = <?cs var:cal.prev.month ?>; form.submit();" />
    </td>
    <td align="center">
        <select name="year">
             <?cs loop:y = "2002", "2012", "1" ?>
             <option value="<?cs var:y ?>" <?cs if:y == cal.current.year ?>selected<?cs /if ?>><?cs var:y ?></option>
             <?cs /loop ?>
        </select>
        年
        <select name="month">
             <?cs loop:m = "1", "12", "1" ?>
             <option value="<?cs var:m ?>" <?cs if:m == cal.current.month ?>selected<?cs /if ?>><?cs var:m ?></option>
             <?cs /loop ?>
        </select>
        月
    </td>
    <td align="right">
       <input type="button" value="<?cs var:cal.next.month ?>月&gt;&gt;" onclick="form.year.value = <?cs var:cal.next.year ?>; form.month.value = <?cs var:cal.next.month ?>; form.submit();"/>
    </td>
  </tr>
</table>
</form>

<table class="list with-cells">
<thead>
<tr>
<th></th>
    <th style="width: 14%;">日曜日</th>
    <th style="width: 14%;">月曜日</th>
    <th style="width: 14%;">火曜日</th>
    <th style="width: 14%;">水曜日</th>
    <th style="width: 14%;">木曜日</th>
    <th style="width: 14%;">金曜日</th>
    <th style="width: 14%;">土曜日</th>
    </tr>
</thead>

<tbody>
<?cs each:w = cal.weeks ?>
  <tr style="height: 60px;">
    <th></th>
    <?cs each:d = w ?>
    <span> 
      <td class="<?cs var:d.cls ?>" style="width: 14%;" valign="top">
      <div class="textright"><?cs var:d.mday.day ?></div>
      <?cs each:t = d.tickets ?>
      <span>
        <div class="ticket">
          <img src="<?cs var:t.img_url ?>" alt="+" />
          <a href="<?cs var:t.url ?>">
            <span class="type"><?cs var:t.ticket['type'] ?></span>
            <?cs if:t.ticket['status'] == 'closed' ?><s><?cs /if ?>
            #<?cs var:t.ticket['id'] ?>:<?cs var:t.ticket['summary'] ?>
            <?cs if:t.ticket['status'] == 'closed' ?></s><?cs /if ?>
          </a>
          <span class="tip">
            <pre><span class="type"><?cs var:t.ticket['type'] ?></span>#<?cs var:t.ticket['id'] ?>: <?cs var:t.ticket['summary'] ?></pre>
            <strong>担当者</strong>: <?cs var:t.ticket['owner'] ?><br />
            <strong>開始日</strong>: <?cs var:t.ticket['due_assign'] ?><br />
            <strong>終了日</strong>: <?cs var:t.ticket['due_close'] ?><br />
            <strong>詳細</strong>: <pre><?cs var:t.ticket['description'] ?></pre>
          </span>
        </div>
      </span>
      <?cs /each ?>

      <?cs each:m = d.milestones ?>
      <span>
        <div class="ticket">
          <a href="<?cs var:m.url ?>">
            <?cs if:m.milestone['completed'] == True ?><s><?cs /if ?>
            <img src="<?cs var:m.img_url ?>" /><?cs var:m.milestone['name'] ?>
            <?cs if:m.milestone['completed'] == True ?></s><?cs /if ?>
          </a> 
          <span class="tip">
            <?cs var:m.milestone['name'] ?><br />
            <strong>期限</strong>: <?cs var:m.milestone['due'] ?><br />
            <strong>詳細</strong>: <?cs var:m.milestone['description'] ?><br />
          </span>
        </div>
      </span>
      <?cs /each ?>
    </td>
    </span>
    <?cs /each ?>
  </tr>
<?cs /each ?>
</tbody>
</table>

<?cs include "footer.cs" ?>
