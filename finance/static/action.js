
/****************** history.html *******************
Applies bootstrap datatable to history table
*/
function getHistoryDataTable() {
    $(document).ready(function() {
    $('#history').DataTable();
} );}



/****************** layout.html *******************
Displays username as dropdown text, "Account" if query fails
*/
function getNavbarAccountName () {
    document.addEventListener("DOMContentLoaded", function getAccountName() {
        var accountName = document.querySelector('#accountName');

        $.get("/get_account_name", function(data) {
            if (data) {
                accountName.innerHTML = data;
            }
            else {
                accountName.innerHTML = "Account";
            }
        })
    })
}


/****************** quote.html *******************
Gets the company name of input symbol, "Invalid symbol" otherwise
*/
function getCompanyName() {
    var symbol = document.querySelector('input[name="symbol"]');
    var status = document.querySelector('p[class="status"]');

    $.get("/check_symbol?symbol="+symbol.value, function(data) {
        if (data) {
            status.innerHTML = data;
        }
        else {
            status.innerHTML = "Invalid symbol";
            event.preventDefault();
        }
    })
}


/****************** register.html *******************
Check username before registering user
*/
function checkUsernameAvailable() {
    var username = document.querySelector('input[name="username"');
    var status = document.querySelector('p[class="status"');

    $.get("/check?username="+username.value, function(data){
        if (data == true){
            status.innerHTML = "Username " + username.value +" available";
        }
        else {
            status.innerHTML = "Username " + username.value + " not available";
            event.preventDefault();
        }
    })
}


/****************** change_username.html *******************
Check if username is available
*/
function checkIfUsernameAvailable() {
    var username = document.querySelector('input[name="username"]');
    var status = document.querySelector('p[class="status"]');

    $.get("/check?username="+username.value, function(data){
        if (data == true){
            status.innerHTML = "Username " + username.value +" available";
        }
        else {
            status.innerHTML = "Username " + username.value + " not available";
            event.preventDefault();
        }
    })
}




/****************** change_password.html *******************
Check if password is available
*/
// function checkNewPassword() {
//     var password = document.querySelector('input[name="password_old"]');
//     var status = document.querySelector('p[class="status"]');

//     $.get("/check?username="+username.value, function(data){
//         if (data == true){
//             status.innerHTML = "Username " + username.value +" available";
//         }
//         else {
//             status.innerHTML = "Username " + username.value + " not available";
//             event.preventDefault();
//         }
//     })
// }
