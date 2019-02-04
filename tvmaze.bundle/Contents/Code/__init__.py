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
    Log.Debug("Starting TVMaze Agent")


class TVMazeAgent(Agent.TV_Shows):
    name = "TV Maze"
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
        Log.Debug("Search with TVMazeAgent: " + media.show)
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
        show = tvm.get_show(maze_id=int(metadata.id))
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

        # Genres
        try: metadata.genres = show.genres
        except: metadata.genres = None
        
        # Studio
        try: metadata.studio = show.network.name
        except: metadata.studio = None

        # Get poster if it exists
        if show.image:
            if show.image.get('medium'):
                med_url = show.image.get('medium')
                if not med_url in metadata.posters.keys():
                    metadata.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
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
                if seasons[int(s)].image.get('medium'):
                    med_url = seasons[int(s)].image.get('medium')
                    if not med_url in season.posters.keys():
                        season.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
                if seasons[int(s)].image.get('original'):
                    orig_url = seasons[int(s)].image.get('original')
                    if not orig_url in season.posters.keys():
                        season.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)
            elif show.image:
                if show.image.get('medium'):
                    med_url = show.image.get('medium')
                    season.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
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
            episode.title = ep.title
            episode.summary = ep.summary
            episode.index = ep.episode_number
            episode.season = ep.season_number
            try:
                airdate = datetime.datetime.strptime(ep.airdate, '%Y-%m-%d')
            except TypeError as e:
                airdate = ep.airdate
            episode.originally_available_at = airdate
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
