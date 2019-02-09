#!/usr/bin/python

import os
import re
import datetime
import pytvmaze


SUPPORTED_LANGUAGES = [
    'ab', 'sq', 'ar', 'hy', 'az', 'bg', 'zh', 'cs', 'da', 'nl', 'en', 'et',
    'fi', 'fr', 'ka', 'de', 'ga', 'he', 'hi', 'hr', 'hu', 'is', 'it', 'ja',
    'ko', 'no', 'fa', 'pl', 'pt', 'ro', 'ru', 'sr', 'es', 'sv', 'tl', 'th',
    'tr', 'uk', 'ur', 'cy']


def Start():
    Log.Debug("Starting TVmaze Agent")


class TVmazeAgent(Agent.TV_Shows):
    name = "TVmaze"
    languages = SUPPORTED_LANGUAGES
    primary_provider = True
    fallback_agent = False
    accepts_from = None
    contributes_to = None


    # Search for YYYY-MM-DD formatted date
    def regex_date(self, filename):
        re1=('((?:(?:[1]{1}\\d{1}\\d{1}\\d{1})|(?:[2]{1}\\d{3}))[-:\\/.]'
             '(?:[0]?[1-9]|[1][012])[-:\\/.](?:(?:[0-2]?\\d{1})|(?:[3][01]'
             '{1})))(?![\\d])')
        rg = re.compile(re1,re.IGNORECASE|re.DOTALL)
        m = rg.search(filename)
        if m:
            date = m.group()
            return date

    # Search for S01E01 formatted info
    def regex_sxxexx(self, filename):
        re1='(S)'
        re2='(\\d+)'
        re3='(E)'
        rg = re.compile(re1+re2+re3+re2,re.IGNORECASE|re.DOTALL)
        m = rg.search(filename)
        if m:
            ep_info = m.group()
            return ep_info


    def search(self, results, media, lang, manual):
        Log.Debug("Search with TVmazeAgent: " + media.show)
        shows = pytvmaze.get_show_list(media.show)
        if shows:
            scores = [show.score for show in shows]
            for show in shows:
                Log.Debug(media.show)
                Log.Debug(show.name + ' ' + str(show.maze_id))

                if show.language:
                    lang_code = Locale.Language.Match(show.language)
                    Log.Debug('{lang} ({code})'.format(lang=show.language,
                                                       code=lang_code))
                else:
                    lang_code = lang

                # Scale scores
                if len(scores) > 1:
                    new_score = ((99 * (show.score - min(scores))) / (max(scores) - min(scores))) + 1
                else:
                    new_score = scores[0]

                results.Append(MetadataSearchResult(
                    id = str(show.maze_id),
                    name = show.name,
                    year = int(show.premiered[:4]) if show.premiered else None,
                    lang = lang_code,
                    score = int(new_score)
                ))
                Log.Debug('Result added...')
                Log.Debug(new_score)


    def update(self, metadata, media, lang, force):
        Log.Debug('Update() called...')

        # Get main show info
        tvm = pytvmaze.TVMaze()
        show = tvm.get_show(maze_id=int(metadata.id), embed='cast')
        if not show:
            return

        # Title
        metadata.title = show.name
        
        # Summary
        try: metadata.summary = show.summary
        except: metadata.summary = None

        # Year
        try: metadata.originally_available_at = datetime.datetime.strptime(show.premiered, '%Y-%m-%d')
        except: metadata.originally_available_at = None
        
        # Duration
        try: metadata.duration = show.runtime
        except: metadata.duration = None

        # Rating
        try: metadata.rating = show.rating.get('average')
        except: metadata.rating = None

        # Content Rating - TVmaze doesn't provide content rating, so let's use the show's status (Running, Ended, Cancelled, etc)
        try: metadata.content_rating = show.status
        except: metadata.content_rating = None

        # Genres
        try: metadata.genres = show.genres
        except: metadata.genres = None
        
        # Studio - Add country code?
        if show.network:
            try: metadata.studio = show.network.name
            except: metadata.studio = None
        elif show.web_channel:
            try: metadata.studio = show.web_channel.name
            except: metadata.studio = None
        else:
            metadata.studio = None
        
        # Cast
        try:
            cast_data = zip(show.cast.people, show.cast.characters)
            _ = (e for e in cast_data)  # test if cast data is iterable ie not null

            metadata.roles.clear()
            for person, character in cast_data:
                try:
                    role = metadata.roles.new()
                    role.role = character.name
                    role.name = person.name
                    # Prefer character over actor photo.
                    if character.image:
                        role.photo = character.image.get('original')
                    elif person.image:
                        role.photo = person.image.get('original')
                    else:
                        role.photo = None
                except:
                    pass
        except AttributeError:
            pass

        # Get poster if it exists
        if show.image:
            if show.image.get('original'):
                orig_url = show.image.get('original')
                if not orig_url in metadata.posters.keys():
                    metadata.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)

        # Get season posters they exist
        seasons = pytvmaze.show_seasons(int(metadata.id))
        for s in seasons:
            # Get the season object from the model
            season = metadata.seasons[seasons[s].season_number]
            if seasons[int(s)].image:
                if seasons[int(s)].image.get('original'):
                    orig_url = seasons[int(s)].image.get('original')
                    if not orig_url in season.posters.keys():
                        season.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)
            elif show.image:
                if show.image.get('original'):
                    orig_url = show.image.get('original')
                    season.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)

        # Get episode info
        episodes = pytvmaze.episode_list(metadata.id)
        for ep in episodes:
            # Get the episode object from the model
            episode = metadata.seasons[ep.season_number].episodes[ep.episode_number]

            # Populate metadata attributes
            episode.show = show.name

            # Title
            try: episode.title = ep.title
            except: episode.title = None

            # Summary
            try: episode.summary = ep.summary
            except: episode.summary = None

            # Season
            try: episode.season = ep.season_number
            except: episode.season = None

            # Episode
            try: episode.index = ep.season_number
            except: episode.index = None

            # Air date
            try: airdate = datetime.datetime.strptime(ep.airdate, '%Y-%m-%d')
            except: airdate = ep.airdate
            try: episode.originally_available_at = airdate
            except: episode.originally_available_at = None

            # Duration
            episode.duration = ep.runtime

            # Download the episode thumbnail
            valid_names = list()

            if ep.image.get('original'):
                thumb_url = ep.image.get('original')
                if thumb_url is not None and len(thumb_url) > 0:
                    # Check that the thumb doesn't already exist before downloading it
                    valid_names.append(thumb_url)
                    if thumb_url not in episode.thumbs:
                        try:
                            episode.thumbs[thumb_url] = Proxy.Media(HTTP.Request(thumb_url).content)
                        except:
                            # tvmaze doesn't have a thumb for this show
                            pass
