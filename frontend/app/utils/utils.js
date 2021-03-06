var $body = $('body');
$body.on('blur', 'input[name^="phone"]', function() {
    // Format telephone number
    var $phoneNumberInput = $(this);
    var phone = $phoneNumberInput.val();
    if (phone.match(/[a-z]|[A-Z]/)) {
        // if letters are found, skip formatting: it may not be a phone field after all
        return false;
    }

    // Match on mobile phone nrs e.g. +316 or 06, so we can automatically set the type to mobile.
    if (phone.match(/^\+316|^06/)) {
        var typeId = $phoneNumberInput.attr('id').replace('raw_input', 'type');
        $('#' + typeId).select2('val', 'mobile');
    }

    phone = phone
        .replace("(0)","")
        .replace(/\s|\(|\-|\)|\.|\\|\/|\–|x|:|\*/g, "")
        .replace(/^00/,"+");

    if (phone.length == 0) {
        return false;
    }

    if (!phone.startsWith('+')) {
        if (phone.startsWith('0')) {
            phone = phone.substring(1);
        }
        phone = '+31' + phone;
    }

    if (phone.startsWith('+310')) {
        phone = '+31' + phone.substring(4);
    }
    $phoneNumberInput.val(phone);
});

$body.on('change', 'select[id*="is_primary"]', function (e) {
    if ($(e.currentTarget).val() == 'True') {
        $('select[id*="is_primary"]').each(function (i) {
            if ($(this).is('select') && $(this).val() == 'True') {
                $(this).val('False');
            }
        });
        $(e.currentTarget).val('True');
        HLSelect2.init();
    }
});
