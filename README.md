**This Agent is incomplete, I need your help**

I am posting this here because I would love the help of people who are familiar with Plex metadata agents.  I have just a couple issues I would like to iron out before considering this complete, and of course any other suggestions on what I have are welcome!

*Issue #1:*
    Line 70 bothers me.  I have tried to use the suggested ```Locale.Language.Unknown``` when a language code is not found, but that results in the Update() method not being called on that show and therefore the show doesn't show up in Plex.  Would love some help with this because defaulting to English doesn't seem right.

*Issue #2:*
    Date-based series (talkshows).  I'm having trouble getting something like "Conan - 2016-01-04.mkv" to show up correctly.  I've had to resort to renaming my talkshows with their season and episode numbers instead to get this agent to work.  I'd love to be able to support the date-based conventions shown [here](https://support.plex.tv/hc/en-us/articles/200381053-Naming-Date-based-TV-Shows).  In my testing, I noticed that some years showed up ok while other entire years of a date-based show didn't show up properly.

Thanks!
