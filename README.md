# flask-places-proxy
Flask example that is a proxy and cache for Google Places API Results. Further, it acts as a real running example of
`rekt_googleplaces`.

## Running the Code

1. Add your Google Places API Key under the `debug` section of `app/defaults.yaml`. You may need to create a google developer account.
2. Install the dependencies in requirements.txt (virtualenv is your friend).
3. `run.py debug server`
4. `run.py debug example`

## Why?

**Working with GooglePlaces Is Burdensome**

Using the Google Places API from Python is a PITA. So for myself and posterity I have
written client libraries and example code to show how to do it lazymode rather than
hardmode.

The Google Places Webservice API does not give you all the information you need in one call.
In the places search you only get the high level information about up to 60 places that match
a give search. The first hassle is that to get all 60, this requires pagination of 3 pages of 20. There
seems to be some eventual consistency of the page_token that slows things down even more.

After you get all of the high level details, to get the specific details (hours, photo refs, etc)requires an API call per
place. When done sequentially this means 63 API calls. This service proxy reduces the overhead
to exactly 1 api call and utilizes asynchronous service calls to the Google Places API to make all of the PlaceDetails
requests in parallel.

**Caching and Resource Loading**

The second part is fetching photos. Photos are their own hassle since they are, rightfully,
not nice JSON responses. Generally, photos are also bigger than JSON responses so I show
how to use a generic resource_loader backed by a cache in order to abstract cache from
loading of a resource. The resource_loader allows you to have a global mapping of
service defined url schemes to resource loading callbacks. This decouples your resource
persistence and management mechanism from your API in a way that allows you to
swap it out generically for another as the need arises wihtout changes in API code.

You should notice that it takes about 3x longer on the debug server to fetch from the GooglePlaces API
as it does from a locally cached image.

**Configuring Services for Multiple Runtime Domains**

The config module uses a hierarchical YAML configuration. The configuration sections map
to specific run configurations. This show how to have a base configuration that is common
to your local testing, preproduction, production, and other scenarios. I have used this pattern for local vs. docker vs ec2.