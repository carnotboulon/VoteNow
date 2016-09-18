/*Activate or deactivate item*/
function select(li)
{
	if ($(li).hasClass("selected"))
	{
		$(li).removeClass("selected");
	}
	else
	{
		$(li).addClass("selected");
	}
}

/*Activate item and deactivate others*/
function toggle(li)
{
	alert("bonjour")
	$(li).parent().find('li').each(function (){
		$(this).addClass("selected");
	})
	
}
