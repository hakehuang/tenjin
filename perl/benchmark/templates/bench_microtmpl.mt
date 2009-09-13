<? my ($_context) = @_; ?>
<? my $list = $_context->{list}; ?>
   <tbody>
    <? my $n = 0; ?>
    <? for my $item (@$list) { ?>
    <?   $n += 1; ?>
    <tr class="<?= $n % 2 == 0 ? 'even' : 'odd' ?>">
     <td style="text-align: center"><?= $n ?></td>
     <td>
      <a href="/stocks/<?= $item->{symbol} ?>"><?= $item->{symbol} ?></a>
     </td>
     <td>
      <a href="<?= $item->{url} ?>"><?= $item->{name} ?></a>
     </td>
     <td>
      <strong><?= $item->{price} ?></strong>
     </td>
     <? if ($item->{change} < 0.0) { ?>
     <td class="minus"><?= $item->{change} ?></td>
     <td class="minus"><?= $item->{ratio} ?></td>
     <? } else { ?>
     <td><?= $item->{change} ?></td>
     <td><?= $item->{ratio} ?></td>
     <? } ?>
    </tr>
    <? } ?>
   </tbody>
