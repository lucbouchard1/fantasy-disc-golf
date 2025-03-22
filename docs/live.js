
scores = {
    1:	100,
    2:	50,
    3:	35,
    4:	27,
    5:	22,
    6:	19,
    7:	17,
    8:	15,
    9:	14,
    10:	13,
    11:	12,
    12:	11,
    13:	10,
    14:	10,
    15:	9,
    16:	9,
    17:	9,
    18:	9,
    19:	9,
    20:	8,
    21:	8,
    22:	8,
    23:	8,
    24:	8,
    25:	7,
    26:	7,
    27:	7,
    28:	7,
    29:	7,
    30:	6,
    31:	6,
    32:	6,
    33:	6,
    34:	6,
    35:	6,
    36:	6,
    37:	6,
    38:	6,
    39:	6,
    40:	5,
    41:	5,
    42:	5,
    43:	5,
    44:	5,
    45:	5,
    46:	5,
    47:	5,
    48:	5,
    49:	5,
    50:	5,
}

function getPoints(place) {
    if (place in scores) {
        return scores[place];
    }
    return 0;
}

function sumInputs(player) {
    var inputs = document.getElementsByClassName(player + '-input');
    var points = document.getElementsByClassName(player + '-points');
    var total = document.getElementById(player + '-total');
    var sum = 0;
    for (var i = 0; i < inputs.length; i++) {
        var place = parseInt(inputs[i].value) || 0;
        var score = getPoints(place);
        points[i].textContent = score.toString();
        sum += score;
    }
    total.textContent = sum.toString();
}