# AED


Our project's goal is to provide an automated detection of authorization vulnerabilities; in effect, provide authorization enforcement in websites. We want to provide administrators or their representatives (white-hat pen-testers, etc.) with the knowledge of if and how an attacker can bypass authorization access control.

The proxy is taken from another github project - https://github.com/inaz2/proxy2


## Usage

Just run as a script:

```
$ python aed_proxy.py
```

Above command runs the proxy on tcp/8080.
To use another port, specify the port number as the first argument.

```
$ python aed_proxy.py 3128
```


## Enable HTTPS intercept

To intercept HTTPS connections, generate private keys and a private CA certificate:

```
$ ./setup_https_intercept.sh
```

Through the proxy, you can access http://proxy2.test/ and install the CA certificate in the browsers.

The above proxy is merely use to intercept the traffic, the analysis is the next step.
The intercepted traffic is saved in "./Traffic/". 

## Starting The Analysis

to start the analysis use SIGINT (ctrl + c).
the following text will be presented: press y
```
Do you want to preform analysis? [y/n]: y
```
after that you are required to enter cookie :
```
Enter cookie: phpseed:asdf3w42r2f2f2f233crebge
```
The cookie should be of a not admin user on the site.

when this is step is finished you will have the result in the following format:
req num result
```
req  14 passed
req  15 ok
```
"passed" means that the request has accepted even so that the cookies weren't admin's.
you can see the original request in "./Traffic/num/num_req.json".


## How the analysis works

Basiclly, ssdeep for comparing response ,token pattern matching for handling nonces, csrf-token and more...

Created by : Tiko and Ehood.


